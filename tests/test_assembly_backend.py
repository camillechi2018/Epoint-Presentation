"""Platform selection must not silently downgrade Office failures or acceptance."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from assembly_backend import select_backend
import doctor
import run_presentation as workflow

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / 'assets/minimal-template-pack'


class AssemblyBackendTests(unittest.TestCase):
    def test_default_selection_and_explicit_override(self):
        for system, expected in [('Windows', 'powerpoint'), ('Darwin', 'native'), ('Linux', 'native')]:
            with self.subTest(system=system):
                self.assertEqual(select_backend(system=system), expected)
                self.assertEqual(select_backend('native', system=system), 'native')
                self.assertEqual(select_backend('powerpoint', system=system), 'powerpoint')

    def test_legacy_alias_conflicts_and_unknown_platform(self):
        self.assertEqual(select_backend(legacy_native=True, system='Windows'), 'native')
        with self.assertRaisesRegex(ValueError, 'ASSEMBLY_BACKEND_CONFLICT'):
            select_backend('powerpoint', legacy_native=True)
        with self.assertRaisesRegex(ValueError, 'ASSEMBLY_PLATFORM_UNSUPPORTED'):
            select_backend(system='Unknown')
        with self.assertRaisesRegex(ValueError, 'ASSEMBLY_BACKEND_UNKNOWN'):
            select_backend('guess')

    def preflight(self, system, **kwargs):
        with patch('platform.system', return_value=system), \
             patch.object(workflow, 'probe_office', side_effect=AssertionError('Office called')):
            return workflow.preflight({'theme': 'blue'}, library=LIBRARY, **kwargs)

    def test_mac_and_linux_default_preflight_need_no_office_or_experimental_flag(self):
        for system in ('Darwin', 'Linux'):
            with self.subTest(system=system):
                report = self.preflight(system)
                self.assertEqual(report['status'], 'ready')
                self.assertTrue(report['can_make_complete_deck'])
                self.assertEqual(report['assembly_backend'], 'native')
                self.assertFalse(report['runtime']['can_render_in_powerpoint'])

    def test_explicit_powerpoint_on_non_windows_is_still_blocked(self):
        for system in ('Darwin', 'Linux'):
            report = self.preflight(system, assembly_backend='powerpoint')
            self.assertEqual(report['status'], 'blocked')
            self.assertEqual(report['error_code'], 'PPTX_BACKEND_UNAVAILABLE')

    def test_windows_missing_office_does_not_silently_use_native(self):
        with patch('platform.system', return_value='Windows'), \
             patch.object(workflow, 'probe_office', return_value={'status': 'unavailable'}):
            report = workflow.preflight({'theme': 'blue'}, library=LIBRARY)
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['assembly_backend'], 'powerpoint')
        self.assertEqual(report['error_code'], 'PPTX_BACKEND_UNAVAILABLE')
        self.assertEqual(self.preflight('Windows', assembly_backend='native')['status'], 'ready')

    def test_native_dependency_missing_blocks_before_generation(self):
        real = workflow.importlib.util.find_spec
        with patch.object(workflow.importlib.util, 'find_spec',
                          side_effect=lambda name: None if name == 'lxml' else real(name)):
            report = self.preflight('Linux')
        self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['runtime']['native_backend_available'])

    def test_native_still_enforces_library_integrity(self):
        with patch.object(workflow, 'resolve_library', side_effect=ValueError('LIBRARY_HASH_FAILED: catalog.json')):
            report = self.preflight('Darwin')
        self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['library_connected'])

    def test_legacy_preflight_maps_to_native_and_reports_alias(self):
        report = self.preflight('Darwin', native_experimental=True)
        self.assertEqual(report['assembly_backend'], 'native')
        self.assertTrue(any('--native-experimental' in message for message in report['warnings']))

    def test_doctor_and_workflow_select_same_backend_without_office(self):
        for system in ('Darwin', 'Linux'):
            with self.subTest(system=system), patch('platform.system', return_value=system), \
                 patch.object(doctor, 'probe_import', return_value={'status': 'available'}), \
                 patch.object(doctor, 'probe_command', return_value={'status': 'available'}), \
                 patch.object(doctor, 'probe_font_profile', return_value={'status': 'available'}), \
                 patch.object(doctor, 'probe_native_backend', return_value={
                     'status': 'available', 'validation': 'import_only', 'error_code': None}), \
                 patch.object(doctor, 'probe_office', side_effect=AssertionError('Office called')):
                report = doctor.report(library=LIBRARY, goal='assemble')
                self.assertEqual(report['status'], 'passed')
                self.assertEqual(report['assembly']['backend'], 'native')
                self.assertEqual(report['assembly']['validation'], 'import_only')

    def test_native_does_not_ignore_requested_office_smoke(self):
        with self.assertRaisesRegex(ValueError, 'OFFICE_SMOKE_REQUIRES_POWERPOINT_BACKEND'):
            doctor.report(assembly_backend='native', office_smoke=True)


if __name__ == '__main__':
    unittest.main()
