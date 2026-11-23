"""Rechecking a manifest must use the current file bytes and the resolved root."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from distribution import safe_file, verify_manifest


class ManifestTests(unittest.TestCase):
    def test_each_verification_rechecks_assets_and_rejects_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            catalog = root / 'catalog.json'
            catalog.write_bytes(b'{}')
            manifest = {'files': {'catalog.json': hashlib.sha256(b'{}').hexdigest()}}
            (root / 'knowledge-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            self.assertEqual(verify_manifest(folder), manifest)
            self.assertEqual(safe_file(folder, 'catalog.json'), catalog.resolve())
            catalog.write_bytes(b'[]')
            with self.assertRaisesRegex(ValueError, 'manifest_hash_mismatch'):
                verify_manifest(folder)
            catalog.unlink()
            with self.assertRaisesRegex(ValueError, 'manifest_missing_or_unsafe_file'):
                verify_manifest(folder)
            catalog.write_bytes(b'{}')
            manifest['files']['../catalog.json'] = manifest['files']['catalog.json']
            (root / 'knowledge-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'manifest_invalid_path'):
                verify_manifest(folder)
