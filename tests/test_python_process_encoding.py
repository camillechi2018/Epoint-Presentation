"""Installer Python children emit strict UTF-8 independently of the host locale."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import runtime_process
import install_runtime


class PythonEncodingTests(unittest.TestCase):
    def test_installer_child_overrides_legacy_encoding_without_changing_parent(self):
        with patch.dict(os.environ, {'PYTHONUTF8': '0', 'PYTHONIOENCODING': 'gbk'}):
            result = install_runtime.capture([sys.executable, '-c',
                "import os,sys; print('中文目录'); print(os.environ['EPOINT_ENCODING_TEST']); print('错误提示',file=sys.stderr)"],
                env={**os.environ, 'EPOINT_ENCODING_TEST': 'preserved'})
            self.assertIsNone(result['error'])
            self.assertEqual(result['returncode'], 0)
            self.assertIn('中文目录', result['stdout'])
            self.assertIn('preserved', result['stdout'])
            self.assertIn('错误提示', result['stderr'])
            self.assertEqual(os.environ['PYTHONIOENCODING'], 'gbk')
            self.assertEqual(os.environ['PYTHONUTF8'], '0')

    def test_corrupt_child_bytes_are_still_rejected(self):
        result = install_runtime.capture([sys.executable, '-c', "import os; os.write(1,bytes([255]))"])
        self.assertEqual(result['error'], 'PROCESS_ENCODING_ERROR')

    def test_generic_capture_stays_strict_and_does_not_change_protocol(self):
        result = runtime_process.capture([sys.executable, '-c', "print('中文')"],
                                         env={**os.environ, 'PYTHONIOENCODING': 'gbk'})
        self.assertEqual(result['error'], 'PROCESS_ENCODING_ERROR')


if __name__ == '__main__':
    unittest.main()
