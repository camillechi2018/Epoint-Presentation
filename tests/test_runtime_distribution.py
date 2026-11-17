"""Verify the install allowlist preserves runtime scripts/resources and excludes dev files."""
import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]


class RuntimeDistributionTests(unittest.TestCase):
    def test_exact_allowlist_contains_all_runtime_files(self):
        files=json.loads((ROOT/'distribution-files.json').read_text(encoding='utf-8'))['files']
        self.assertEqual(len(files),len(set(files)))
        for name in files:
            self.assertTrue((ROOT/name).is_file(),name)
            self.assertFalse(name.startswith(('tests/','tools/','.git/')))
        for p in (ROOT/'scripts').iterdir():
            if p.is_file():self.assertIn('scripts/'+p.name,files)
        for name in ['office_runtime.py','office_probe.ps1','office_guard.ps1','assemble_deck_worker.ps1','delivery_status.py','export_source_previews.ps1']:
            self.assertIn('scripts/'+name,files)

    def test_documented_script_paths_exist(self):
        for p in [ROOT/'SKILL.md',ROOT/'README.md',*list((ROOT/'references').glob('*.md'))]:
            for name in re.findall(r'scripts/([A-Za-z_][A-Za-z_0-9]*\.(?:py|ps1|cjs))',p.read_text(encoding='utf-8-sig')):
                self.assertTrue((ROOT/'scripts'/name).is_file(),f'{p.name}: {name}')


if __name__=='__main__':unittest.main()
