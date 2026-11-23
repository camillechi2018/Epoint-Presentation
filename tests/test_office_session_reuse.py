import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import office_runtime


class OfficeSessionReuseTests(unittest.TestCase):
    def test_assembly_and_final_reopen_use_one_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / 'plan.json'
            manifest.write_text('{"slides": [{}]}', encoding='utf-8')
            deck = root / 'deck.pptx'
            images = root / 'rendered'
            smoke_directory = root / 'office-smoke'
            smoke_result = {}

            def worker(script, args, *unused, **options):
                self.assertEqual(script.name, 'assemble_deck_worker.ps1')
                self.assertEqual(args[args.index('-RenderDirectory') + 1], images)
                self.assertEqual(args[args.index('-SmokeDirectory') + 1], smoke_directory)
                self.assertEqual(options['timeout'], 45)
                self.assertEqual(options['phase_timeouts'], [('assembly', 300), ('render', 300)])
                smoke_deck = smoke_directory / 'smoke.pptx'
                smoke_deck.write_bytes(b'one-slide test')
                smoke_images = smoke_directory / 'smoke-render'
                smoke_images.mkdir()
                Image.new('RGB', (8, 8)).save(smoke_images / 'P001.png')
                smoke_evidence = {'status': 'passed', 'opened': True, 'slide_count': 1,
                                  'output_sha256': hashlib.sha256(smoke_deck.read_bytes()).hexdigest()}
                (smoke_directory / 'backend.json').write_text(json.dumps(smoke_evidence), encoding='utf-8')
                deck.write_bytes(b'final deck')
                deck.with_suffix('.assembly.json').write_text('{}', encoding='utf-8')
                Image.new('RGB', (8, 8)).save(images / 'P001.png')
                evidence = {'status': 'passed', 'application': 'Microsoft PowerPoint',
                            'opened': True, 'slide_count': 1,
                            'output_sha256': hashlib.sha256(deck.read_bytes()).hexdigest()}
                (images / 'powerpoint-validation.json').write_text(json.dumps(evidence), encoding='utf-8')

            with patch.object(office_runtime, 'run_worker', side_effect=worker) as run_worker:
                result = office_runtime.assemble(manifest, deck, images, sys.executable, 'windows',
                                                 smoke_directory=smoke_directory, smoke_result=smoke_result)
            self.assertEqual(run_worker.call_count, 1)
            self.assertEqual(smoke_result['status'], 'available')
            self.assertTrue(result['opened'])
            report = json.loads(deck.with_suffix('.assembly.json').read_text(encoding='utf-8'))
            self.assertEqual(report['powerpoint_validation_status'], 'passed')

    def test_reopen_evidence_must_match_the_final_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deck = root / 'final.pptx'
            deck.write_bytes(b'edited after export')
            evidence = {'status': 'passed', 'opened': True, 'slide_count': 1,
                        'output_sha256': hashlib.sha256(b'old deck').hexdigest()}
            (root / 'powerpoint-validation.json').write_text(json.dumps(evidence), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'POWERPOINT_EVIDENCE_INVALID'):
                office_runtime._check_render(deck, root)


if __name__ == '__main__':
    unittest.main()
