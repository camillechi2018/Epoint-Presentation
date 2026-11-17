import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import office_runtime as office
from delivery_status import assess, exit_code


class OfficeDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.deck = self.root / 'deck.pptx'
        self.deck.write_bytes(b'fixture')
        self.images = self.root / 'rendered'
        self.images.mkdir()
        Image.new('RGB', (10, 10)).save(self.images / 'P001.png')
        self.evidence = dict(status='passed', application='Microsoft PowerPoint', opened=True,
                             slide_count=1, output_sha256=hashlib.sha256(b'fixture').hexdigest())

    def test_success_requires_visual_review_and_is_not_deliverable(self):
        result = assess(self.deck, self.images, 1, self.evidence)
        self.assertEqual(result['delivery_status'], 'pending_visual_review')
        self.assertFalse(result['deliverable'])
        self.assertEqual(result['powerpoint_validation_status'], 'passed')
        self.assertNotIn('target_application', result)
        self.assertNotIn('target_application_status', result)
        self.assertEqual(exit_code({'status': 'candidate_created', **result}, True), 3)
        self.assertEqual(exit_code({'status': 'ready'}, False), 0)
        self.assertEqual(exit_code({'status': 'blocked'}, True), 2)

    def test_libreoffice_is_only_preview(self):
        evidence = {**self.evidence, 'application': 'LibreOffice'}
        result = assess(self.deck, self.images, 1, evidence)
        self.assertEqual(result['delivery_status'], 'pending_powerpoint_validation')
        self.assertEqual(result['powerpoint_validation_status'], 'not_verified')

    def test_stale_evidence_cannot_validate_changed_deck(self):
        self.deck.write_bytes(b'changed')
        self.assertEqual(assess(self.deck, self.images, 1, self.evidence)['delivery_status'], 'pending_powerpoint_validation')

    def test_existing_images_cannot_hide_render_failure(self):
        result = assess(self.deck, self.images, 1, {'status': 'failed', 'error_code': 'RENDER_FAILED'})
        self.assertEqual(result['delivery_status'], 'pending_render')
        self.assertEqual(result['render_status'], 'failed')

    def test_missing_or_corrupt_image_blocks_acceptance(self):
        self.assertEqual(assess(self.deck, self.images, 2, self.evidence)['delivery_status'], 'pending_render')
        (self.images / 'P001.png').write_bytes(b'not png')
        self.assertEqual(assess(self.deck, self.images, 1, self.evidence)['delivery_status'], 'pending_render')

    def test_unidentified_application_cannot_pass(self):
        evidence = {**self.evidence, 'application': 'PowerPoint-compatible'}
        self.assertEqual(assess(self.deck, self.images, 1, evidence)['delivery_status'], 'pending_powerpoint_validation')

    def test_timeout_is_bounded_recorded_and_cleans_only_owned_process(self):
        with patch.object(office.shutil, 'which', return_value='powershell'), \
             patch.object(office.subprocess, 'run', side_effect=subprocess.TimeoutExpired('worker', 1)), \
             patch.object(office, '_cleanup_owned', return_value='no_owned_process_recorded') as cleanup:
            with self.assertRaisesRegex(RuntimeError, 'OFFICE_OPERATION_TIMEOUT'):
                office.run_worker('worker.ps1', [], self.root, timeout=1)
        cleanup.assert_called_once_with('powershell', self.root / 'office-owner.json')
        self.assertEqual(json.loads((self.root / 'office-process.json').read_text())['error_code'], 'OFFICE_OPERATION_TIMEOUT')

    def test_no_cleanup_without_ownership_record(self):
        with patch.object(office.subprocess, 'run') as run:
            office._cleanup_owned('powershell', self.root / 'missing.json')
        run.assert_not_called()

    def test_existing_render_directory_is_rejected(self):
        with patch.object(office, 'run_worker') as worker:
            with self.assertRaises(FileExistsError):
                office.render(self.deck, self.images)
        worker.assert_not_called()

    def test_smoke_failure_cannot_become_available(self):
        def fail(*args, **kwargs):
            (self.root / 'backend.json').write_text(json.dumps({'status': 'failed', 'error_code': 'OFFICE_BACKEND_UNSUPPORTED'}))
            raise RuntimeError('OFFICE_OPERATION_FAILED')
        with patch.object(office.os, 'name', 'nt'), patch.object(office, 'run_worker', side_effect=fail):
            result = office.probe(smoke=True, directory=self.root)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['error_code'], 'OFFICE_BACKEND_UNSUPPORTED')

    @unittest.skipUnless(os.name == 'nt', 'Windows worker integration')
    def test_real_sleeping_worker_times_out(self):
        worker = self.root / 'sleep.ps1'
        worker.write_text('param([string]$OwnerFile)\nStart-Sleep -Seconds 30', encoding='utf-8-sig')
        with self.assertRaisesRegex(RuntimeError, 'OFFICE_OPERATION_TIMEOUT'):
            office.run_worker(worker, [], self.root, timeout=1)

    @unittest.skipUnless(os.name == 'nt', 'Windows registry adapter')
    def test_wps_registered_as_powerpoint_is_rejected(self):
        script = self.root / 'fake-registration.ps1'
        guard = office.SCRIPTS / 'office_guard.ps1'
        script.write_text('''param([string]$Guard)
. $Guard
function Test-Path {return $true}
function Get-Item {
 param([string]$LiteralPath)
 $p=if($LiteralPath){$LiteralPath}else{$args[0]}
 if($p -like '*Registry::*'){
  $x=[pscustomobject]@{}
  $x | Add-Member ScriptMethod GetValue {param($n) 'C:\\WPS\\wpp.exe /Automation'}
  return $x
 }
 return [pscustomobject]@{Name='wpp.exe';FullName='C:\\WPS\\wpp.exe';VersionInfo=[pscustomobject]@{CompanyName='Kingsoft';ProductName='WPS'}}
}
try {Get-EpointPowerPoint;exit 1} catch {if($_.Exception.Message -like 'OFFICE_BACKEND_UNSUPPORTED*'){exit 0};throw}
''', encoding='utf-8-sig')
        result = subprocess.run(['powershell', '-NoProfile', '-File', str(script), str(guard)], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(os.name == 'nt', 'Windows process identity')
    def test_cleanup_requires_matching_process_creation_time(self):
        child = subprocess.Popen(['powershell', '-NoProfile', '-Command', 'Start-Sleep -Seconds 30'],
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        self.addCleanup(lambda: child.kill() if child.poll() is None else None)
        query = '$p=Get-Process -Id ' + str(child.pid) + ';@{pid=$p.Id;started=$p.StartTime.ToUniversalTime().Ticks.ToString();path=$p.Path;owned=$true}|ConvertTo-Json'
        actual = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', query], timeout=10))
        owner = self.root / 'owner.json'
        owner.write_text(json.dumps({**actual, 'started': '0'}), encoding='utf-8')
        office._cleanup_owned('powershell', owner)
        self.assertIsNone(child.poll(), 'Mismatching identity must not stop a process')
        owner.write_text(json.dumps(actual), encoding='utf-8')
        office._cleanup_owned('powershell', owner)
        child.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
