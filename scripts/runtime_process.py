"""Bounded argument-array subprocesses; machine output is decoded strictly."""
import os
import subprocess


def capture_python(args, *, env=None, **kwargs):
    """Set the encoding on controlled Python children, retaining strict decoding.

    Windows pip output can contain localized paths even when its command succeeds.
    Do not change the parent environment or relax the machine-output protocol.
    """
    child_env = {**(os.environ if env is None else env),
                 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
    return capture(args, env=child_env, **kwargs)


def capture(args, *, timeout=15, cwd=None, env=None):
    try:
        run = subprocess.run([str(x) for x in args], cwd=cwd, capture_output=True,
                             timeout=timeout, env=env, shell=False,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
        return {'returncode': run.returncode, 'stdout': run.stdout.decode('utf-8'),
                'stderr': run.stderr.decode('utf-8'), 'error': None}
    except subprocess.TimeoutExpired:
        return {'returncode': None, 'stdout': '', 'stderr': '', 'error': 'PROCESS_TIMEOUT'}
    except UnicodeDecodeError:
        return {'returncode': None, 'stdout': '', 'stderr': '', 'error': 'PROCESS_ENCODING_ERROR'}
    except OSError as exc:
        return {'returncode': None, 'stdout': '', 'stderr': '',
                'error': 'PROCESS_START_FAILED', 'detail': type(exc).__name__}
