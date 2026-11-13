import json
import sys
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation

ROOT = Path(r'C:\Users\xiaoc\.codex\skills\github-knowledge-next')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from content_adapters import adapt_for_layout
from fill_layout import fill
from plan_deck import binding_gap, matches_structural_contract


class OptionalTemplateFieldsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
        cls.entry = next(item for item in catalog['layouts'] if item['id'] == 'content-blue-244')

    def content(self, subtitle=None):
        content = {'type': 'cards', 'structure_type': 'summary',
                   'center': {'title': '能力体系'},
                   'items': [{'heading': f'{i:02d}.能力', 'body': f'服务领域{i}'}
                             for i in range(1, 7)]}
        if subtitle is not None:
            content['center']['subtitle'] = subtitle
        return content

    def test_missing_independent_subtitle_only_clears_its_text(self):
        for theme in ('blue', 'red'):
            with self.subTest(theme=theme), tempfile.TemporaryDirectory() as directory:
                payload, adapter = adapt_for_layout(self.entry['id'], self.content(), '业务概览',
                                                    entry=self.entry)
                self.assertEqual(adapter, 'declared_structural_fields')
                self.assertNotIn('center.subtitle', payload['texts'])
                page = {'role': 'body', 'title': '业务概览', 'content': payload, 'theme': theme}
                self.assertTrue(matches_structural_contract(self.entry, page, {}))
                self.assertEqual(binding_gap(self.entry, page, ROOT, theme), 0)
                source, output = Path(directory) / 'content.json', Path(directory) / 'page.pptx'
                payload['theme'] = theme
                source.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
                report = fill(ROOT, self.entry['id'], source, output, allow_draft=True)
                self.assertEqual(report['omitted_optional_fields'], ['center.subtitle'])
                shapes = {shape.shape_id: shape for shape in Presentation(output).slides[0].shapes}
                self.assertEqual(shapes[48].text, '')
                self.assertEqual(shapes[42].text, '能力体系')
                self.assertIn('服务领域1', [shape.text for shape in shapes.values()
                                         if shape.has_text_frame])

    def test_present_subtitle_is_filled_and_core_field_still_required(self):
        payload, adapter = adapt_for_layout(self.entry['id'], self.content('业务支撑'),
                                            '业务概览', entry=self.entry)
        self.assertEqual(adapter, 'declared_structural_fields')
        self.assertEqual(payload['texts']['center.subtitle'], '业务支撑')
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'content.json', Path(directory) / 'page.pptx'
            payload['theme'] = 'blue'
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            report = fill(ROOT, self.entry['id'], source, output, allow_draft=True)
            self.assertEqual(report['omitted_optional_fields'], [])
            shapes = {shape.shape_id: shape for shape in Presentation(output).slides[0].shapes}
            self.assertEqual(shapes[48].text, '业务支撑')
            payload['texts'].pop('center.title')
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '缺少字段'):
                fill(ROOT, self.entry['id'], source, output, allow_draft=True)

    def test_blank_optional_value_is_treated_as_absent(self):
        payload, _ = adapt_for_layout(self.entry['id'], self.content(), '业务概览',
                                      entry=self.entry)
        payload['texts']['center.subtitle'] = '  '
        payload['theme'] = 'blue'
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'content.json', Path(directory) / 'page.pptx'
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            report = fill(ROOT, self.entry['id'], source, output, allow_draft=True)
            self.assertEqual(report['omitted_optional_fields'], ['center.subtitle'])

    def test_missing_subtitle_does_not_relax_body_capacity(self):
        payload, _ = adapt_for_layout(self.entry['id'], self.content(), '业务概览',
                                      entry=self.entry)
        payload['texts']['aspects[0].body'] = '这段真实正文超过了当前组件允许的文字容量，需要保留原文并换用合适版式。'
        payload['theme'] = 'blue'
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'content.json', Path(directory) / 'page.pptx'
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '超出容量'):
                fill(ROOT, self.entry['id'], source, output, allow_draft=True)


if __name__ == '__main__':
    unittest.main()
