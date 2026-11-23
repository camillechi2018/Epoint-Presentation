"""Bounded Office workers, backend identity and file-bound rendering evidence."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def _cleanup_owned(shell, owner):
    # PID, creation time AND executable must match; never stop processes by name.
    code = ("$ErrorActionPreference='Stop';$r=Get-Content -LiteralPath $args[0] -Raw|ConvertFrom-Json;"
            "if($r.owned){$p=Get-Process -Id $r.pid -ErrorAction SilentlyContinue;"
            "if($p -and $p.Path -ieq $r.path -and $p.StartTime.ToUniversalTime().Ticks.ToString() -eq $r.started){$p.Kill()}}")
    if not owner.is_file():
        return 'no_owned_process_recorded'
    # Use a script file so paths are arguments, never interpolated into shell code.
    script = owner.with_suffix('.cleanup.ps1')
    script.write_text(code, encoding='utf-8-sig')
    try:
        result = subprocess.run([shell, '-NoProfile', '-File', str(script), str(owner)],
                                capture_output=True, timeout=10)
        return 'checked_owned_process' if result.returncode == 0 else 'cleanup_failed'
    except (OSError, subprocess.TimeoutExpired):
        return 'cleanup_failed'


def _communicate_phases(process, report_dir, timeout, phase_timeouts):
    deadline = time.monotonic() + timeout
    for name, budget in phase_timeouts:
        marker = report_dir / f'{name}.started'
        while not marker.is_file():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(process.args, timeout)
            try:
                return process.communicate(timeout=min(remaining, 0.2))
            except subprocess.TimeoutExpired:
                pass
        timeout = budget
        deadline = time.monotonic() + timeout
    return process.communicate(timeout=max(0.001, deadline - time.monotonic()))


def run_worker(script, args, report_dir, *, timeout=180, phase_timeouts=()):
    if not 1 <= timeout <= 3600:
        raise ValueError('OFFICE_TIMEOUT_INVALID')
    shell = shutil.which('pwsh') or shutil.which('powershell')
    if not shell:
        raise RuntimeError('OFFICE_BACKEND_UNAVAILABLE: PowerShell')
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    owner = report_dir / 'office-owner.json'
    if owner.exists():
        raise ValueError('OFFICE_WORK_DIRECTORY_REUSED')
    command = [shell, '-NoProfile', '-File', str(script), *map(str, args), '-OwnerFile', str(owner)]
    result = {}
    try:
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags) as worker:
            try:
                stdout, stderr = _communicate_phases(worker, report_dir, timeout, phase_timeouts)
            except subprocess.TimeoutExpired:
                worker.kill()
                raise
        result = {'returncode': worker.returncode, 'stdout': stdout.decode('utf-8', errors='replace'),
                  'stderr': stderr.decode('utf-8', errors='replace'), 'timeout_seconds': timeout}
        if phase_timeouts:
            result['phase_timeouts'] = dict(phase_timeouts)
    except subprocess.TimeoutExpired as exc:
        result = {'returncode': None, 'error_code': 'OFFICE_OPERATION_TIMEOUT',
                  'timeout_seconds': exc.timeout, 'cleanup': _cleanup_owned(shell, owner)}
    finally:
        (report_dir / 'office-process.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    if result.get('error_code'):
        raise RuntimeError(result['error_code'] + ': ' + str(report_dir))
    if result['returncode']:
        _cleanup_owned(shell, owner)
        raise RuntimeError('OFFICE_OPERATION_FAILED: ' + (result['stderr'] or result['stdout'])[-600:])
    return result


def _empty_presentation(folder):
    from pptx import Presentation

    seed = folder / 'empty-start.pptx'
    with seed.open('xb') as stream:
        Presentation().save(stream)
    return seed


def _check_smoke(folder):
    saved = folder / 'smoke.pptx'
    data = json.loads((folder / 'backend.json').read_text(encoding='utf-8-sig'))
    if (data.get('status') != 'passed' or not data.get('opened') or data.get('slide_count') != 1
            or data.get('output_sha256') != hashlib.sha256(saved.read_bytes()).hexdigest()):
        raise RuntimeError('OFFICE_SMOKE_TEST_FAILED')
    verify_images(folder / 'smoke-render', 1)
    return {**data, 'status': 'available'}


def probe(*, smoke=False, directory=None):
    if os.name != 'nt':
        return {'status': 'unavailable', 'error_code': 'OFFICE_BACKEND_UNAVAILABLE'}
    folder = Path(directory) if directory else Path(tempfile.mkdtemp(prefix='epoint-office-'))
    folder.mkdir(parents=True, exist_ok=True)
    report = folder / 'backend.json'
    try:
        args = ['-Mode', 'smoke' if smoke else 'inspect', '-Report', report]
        if smoke:
            args.extend(['-SeedPresentation', _empty_presentation(folder)])
        run_worker(SCRIPTS / 'office_probe.ps1', args, folder, timeout=45 if smoke else 15)
        return _check_smoke(folder) if smoke else json.loads(report.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        data = json.loads(report.read_text(encoding='utf-8-sig')) if report.is_file() else {}
        code = str(exc).split(':', 1)[0]
        return {**data, 'status': 'unavailable', 'error_code': code if code == 'OFFICE_OPERATION_TIMEOUT' else data.get('error_code', code),
                'detail': data.get('detail', str(exc)), 'report_directory': str(folder)}


def verify_images(directory, count):
    from PIL import Image
    expected = {f'P{i:03d}.png' for i in range(1, count + 1)}
    if count < 1 or {p.name for p in Path(directory).glob('P*.png')} != expected:
        raise ValueError('RENDER_OUTPUT_INCOMPLETE')
    for name in expected:
        with Image.open(Path(directory) / name) as image:
            image.verify()


def _check_render(source, directory):
    data = json.loads((directory / 'powerpoint-validation.json').read_text(encoding='utf-8-sig'))
    if data.get('status') != 'passed' or not data.get('opened') or data.get('output_sha256') != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError('POWERPOINT_EVIDENCE_INVALID')
    verify_images(directory, data['slide_count'])
    return data


def render(source, directory, *, timeout=180):
    source, directory = Path(source), Path(directory)
    # Fresh directory prevents stale images or previous success reports passing a failed run.
    directory.mkdir(parents=True, exist_ok=False)
    run_worker(SCRIPTS / 'office_probe.ps1', ['-Mode', 'render',
               '-Report', directory / 'powerpoint-validation.json',
               '-InputPath', source, '-RenderDirectory', directory], directory, timeout=timeout)
    return _check_render(source, directory)


def assemble(manifest, output, render_directory, python_exe, font_profile, *, timeout=300,
             smoke_directory=None, smoke_result=None):
    if not 1 <= timeout <= 3600:
        raise ValueError('OFFICE_TIMEOUT_INVALID')
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='office-assembly-', dir=output.parent))
    args = ['-Manifest', manifest, '-OutputPath', output, '-PythonExe', python_exe,
            '-FontProfile', font_profile, '-SeedPresentation', _empty_presentation(work)]
    phases = []
    if smoke_directory is not None:
        smoke_directory = Path(smoke_directory)
        smoke_directory.mkdir(parents=True, exist_ok=False)
        args.extend(['-SmokeDirectory', smoke_directory])
        phases.append(('assembly', timeout))
    if render_directory:
        render_directory = Path(render_directory)
        render_directory.mkdir(parents=True, exist_ok=False)
        args.extend(['-RenderDirectory', render_directory])
        phases.append(('render', timeout))
    smoke = None
    try:
        run_worker(SCRIPTS / 'assemble_deck_worker.ps1', args, work,
                   timeout=45 if smoke_directory is not None else timeout, phase_timeouts=phases)
    finally:
        if smoke_directory is not None:
            try:
                smoke = _check_smoke(smoke_directory)
            except (OSError, ValueError, RuntimeError) as exc:
                smoke = {'status': 'unavailable', 'error_code': 'OFFICE_SMOKE_TEST_FAILED',
                         'detail': str(exc), 'report_directory': str(smoke_directory)}
            if smoke_result is not None:
                smoke_result.update(smoke)
    if smoke is not None and smoke['status'] != 'available':
        raise RuntimeError('OFFICE_SMOKE_TEST_FAILED: ' + smoke['detail'])
    evidence = _check_render(output, render_directory) if render_directory else None
    from delivery_status import assess
    plan = json.loads(Path(manifest).read_text(encoding='utf-8-sig'))
    status = assess(output, render_directory or work, len(plan['slides']), evidence)
    sidecar = Path(output).with_suffix('.assembly.json')
    info = json.loads(sidecar.read_text(encoding='utf-8-sig'))
    info.update(status, render_evidence=evidence, rendered=bool(evidence))
    sidecar.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    return evidence


if __name__ == '__main__':
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--render-directory', default='')
    ap.add_argument('--python-exe', default=sys.executable)
    ap.add_argument('--font-profile', default='windows')
    ap.add_argument('--timeout', type=int, default=300)
    a = ap.parse_args()
    assemble(a.manifest, a.output, a.render_directory, a.python_exe, a.font_profile, timeout=a.timeout)
    info = json.loads(Path(a.output).with_suffix('.assembly.json').read_text(encoding='utf-8'))
    print(json.dumps({'status': 'candidate_created', 'delivery_status': info['delivery_status'],
                      'deliverable': False, 'report': str(Path(a.output).with_suffix('.assembly.json'))}))
    raise SystemExit(3)
