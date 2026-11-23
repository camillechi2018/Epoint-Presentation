"""Regression checks for relation, actual count, native selection and fallback."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import atomic_body
from candidate_trial import try_candidate
from content_adapters import adapt_for_layout
from plan_deck import resolve


class AtomicBodyTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.taxonomy = {'relations': {
            'parallel-points': {'aliases': ['并列要点'],
                                'specific_relations': ['work-outcomes', 'issue-actions']},
        }}
        self.write('relation-taxonomy.json', self.taxonomy)
        self.layouts = [
            self.layout('outcomes-original', 4, relation='work-outcomes'),
            self.layout('outcomes-1', 1, 'outcomes-original', 'work-outcomes', ['实际成果']),
            self.layout('outcomes-3', 3, 'outcomes-original', 'work-outcomes', ['实际成果']),
            self.layout('outcomes-5', 5, 'outcomes-original', 'work-outcomes', ['实际成果']),
            self.layout('issues-3', 3, 'issues-original', 'issue-actions', ['问题与举措'],
                        fields=('heading', 'issue', 'action'), page_fields=('summary',)),
        ]
        self.catalog = {'version': 'test', 'layouts': self.layouts}

    def write(self, path, data):
        (self.root / path).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def layout(self, ident, count, parent=None, relation='work-outcomes', aliases=(),
               fields=('heading', 'body'), page_fields=()):
        rules = f'{ident}-rules.json'
        self.write(rules, {'cardinality_mode': 'fixed', 'source_count': count,
                           'supported_counts': [count], 'verified_counts': [count]})
        bindings = f'{ident}-bindings.json'
        paths = ['page.title', *(f'page.{key}' for key in page_fields)]
        paths.extend(f'items[{index}].{key}' for index in range(count) for key in fields)
        self.write(bindings, {'fields': [
            {'field': f'text_{index}', 'semantic_path': path, 'max_chars': 20,
             'max_width_units': 40, 'max_lines': 1}
            for index, path in enumerate(paths)
        ]})
        entry = {'id': ident, 'role': 'content', 'classification_status': 'verified',
                 'pptx_support': 'verified_static', 'status': 'approved', 'themes': ['blue', 'red'],
                 'information_relation': relation, 'canonical_relation': 'parallel-points',
                 'bindings': bindings, 'layout_rules': rules}
        if parent:
            entry['atomic_variant'] = {'parent_id': parent, 'count': count, 'relation': relation,
                                       'aliases': list(aliases), 'item_fields': list(fields),
                                       'page_fields': list(page_fields)}
        return entry

    def page(self, count=3, relation='实际成果', *, content_type='atomic_items'):
        return {'purpose': '交付中的实际成果', 'title': '阶段成果', 'role': 'body',
                'information_relation': relation, 'content': {'type': content_type, 'items': [
                    {'heading': f'成果{index + 1}', 'body': f'完成第{index + 1}项验收'}
                    for index in range(count)
                ]}}

    def plan(self, page, theme='blue'):
        return resolve(self.root, {'theme': theme, 'pages': [page]}, catalog=self.catalog)['pages'][0]

    def test_relation_and_actual_count_select_single_three_and_five(self):
        for count in (1, 3, 5):
            with self.subTest(count=count):
                choice = self.plan(self.page(count))
                self.assertEqual(choice['layout_id'], f'outcomes-{count}')
                self.assertEqual(choice['input_item_count'], count)
                self.assertEqual(choice['atomic_variant'], {
                    'parent_id': 'outcomes-original', 'count': count, 'relation': 'work-outcomes'})
                self.assertEqual(choice['candidate_ids'], [f'outcomes-{count}'])
                self.assertEqual(choice['candidate_summaries'][0]['field_status'], 'ready')

    def test_independent_plans_reread_updated_binding_limits(self):
        page = self.page()
        binding = self.root / 'outcomes-3-bindings.json'
        original = self.plan(page)['candidate_summaries'][0]['capacity_preflight']
        data = json.loads(binding.read_text(encoding='utf-8'))
        data['fields'][0]['max_chars'] = 1
        self.write(binding.name, data)
        updated = self.plan(page)['candidate_summaries'][0]['capacity_preflight']
        self.assertNotEqual(original['binding_sha256'], updated['binding_sha256'])
        self.assertFalse(original['hard_issues'])
        self.assertTrue(any(issue['rule'] == 'max_chars' for issue in updated['hard_issues']))

    def test_old_generic_or_explicit_parent_never_replaced(self):
        generic = self.page(4, 'parallel-points', content_type='cards')
        self.assertEqual(self.plan(generic)['layout_id'], 'outcomes-original')
        parent = self.page(4, 'work-outcomes', content_type='cards')
        parent['layout_id'] = 'outcomes-original'
        self.assertEqual(self.plan(parent)['layout_id'], 'outcomes-original')
        ambiguous = self.page(3, 'parallel-points')
        self.assertEqual(self.plan(ambiguous)['selection_mode'], 'guided_composition')

    def test_ordinary_items_with_specific_relation_and_title_alias(self):
        page = self.page(3, 'parallel-points', content_type='cards')
        page['content']['relation'] = 'WORK-OUTCOMES'
        for item in page['content']['items']:
            item['title'] = item.pop('heading')
        self.assertEqual(self.plan(page)['layout_id'], 'outcomes-3')
        mapped, adapter = adapt_for_layout('outcomes-3', page['content'], page['title'], self.layouts[2])
        self.assertEqual(adapter, 'atomic_items_to_fields')
        self.assertEqual(mapped['texts']['items[0].heading'], '成果1')

    def test_conflicting_count_rejected(self):
        page = self.page(3)
        page['needs'] = {'item_count': 5}
        with self.assertRaisesRegex(ValueError, '实际数量不一致'):
            self.plan(page)
        page['content']['type'] = 'cards'
        with self.assertRaisesRegex(ValueError, '实际数量不一致'):
            self.plan(page)
        page.pop('needs')
        page['content']['item_count'] = True
        with self.assertRaisesRegex(ValueError, '实际数量不一致'):
            self.plan(page)

    def test_regular_payload_keeps_legacy_relation_when_atomic_schema_is_incomplete(self):
        page = self.page(4, 'work-outcomes', content_type='cards')
        for item in page['content']['items']:
            item['legacy_source_note'] = '旧路径字段'
        self.assertEqual(self.plan(page)['layout_id'], 'outcomes-original')

    def test_unknown_count_theme_or_incomplete_fields_without_false_fit(self):
        self.assertEqual(self.plan(self.page(6))['candidate_ids'], [])
        self.assertEqual(self.plan(self.page(), theme='deep-blue-tech')['candidate_ids'], [])
        page = self.page(3, 'issue-actions')
        page['content']['items'][0]['action'] = '安排跟踪'
        page['content']['items'][0]['owner'] = '交付组'
        self.assertEqual(self.plan(page)['candidate_ids'], [])
        fallback = atomic_body.fallback_content(page['content'], page['title'])
        self.assertIn('安排跟踪', fallback['items'][0])
        self.assertIn('交付组', fallback['items'][0])
        self.assertIn('完成第1项验收', fallback['items'][0])

    def test_explicit_child_accepts_complete_native_fields(self):
        page = self.page()
        page.pop('information_relation')
        mapped, _ = adapt_for_layout('outcomes-3', page['content'], page['title'], self.layouts[2])
        page['content'] = {'type': 'template_fields', 'texts': mapped['texts']}
        page['layout_id'] = 'outcomes-3'
        self.assertEqual(self.plan(page)['layout_id'], 'outcomes-3')
        page['content']['texts'].pop('items[2].body')
        self.assertEqual(self.plan(page)['candidate_ids'], [])

    def test_trial_maps_related_fields_and_preserves_source(self):
        entry = self.layouts[-1]
        page = self.page(3, '问题与举措')
        page['content'] = {'type': 'atomic_items', 'page': {'summary': '问题已分类'},
                           'items': [{'heading': f'环节{i}', 'issue': f'问题{i}', 'action': f'行动{i}'}
                                     for i in range(3)]}
        self.assertEqual(self.plan(page)['layout_id'], 'issues-3')
        content = dict(page['content'], theme='blue')
        output = self.root / 'filled.pptx'
        trial = self.root / 'trial.json'
        with patch('candidate_trial.fill', return_value={'source_stamp': 'epoint:source-proof'}) as fill:
            filled, record = try_candidate(self.root, entry, content, page, self.root / 'input.json',
                                           trial, output, allow_draft=True, body_header_pilot=False)
            fill.assert_called_once()
        mapped = json.loads(trial.read_text(encoding='utf-8'))
        self.assertEqual(mapped['item_count'], 3)
        self.assertEqual(mapped['texts']['items[2].action'], '行动2')
        self.assertEqual(mapped['texts']['page.summary'], '问题已分类')
        self.assertEqual(record['source_stamp'], filled['source_stamp'])
        self.assertEqual(record['atomic_variant']['parent_id'], 'issues-original')

    def test_trial_rejects_overcapacity_before_fill(self):
        entry = self.layouts[2]
        page = self.page()
        page['content']['items'][0]['body'] = '字' * 21
        content = dict(page['content'], theme='blue')
        with patch('candidate_trial.fill') as fill:
            filled, record = try_candidate(self.root, entry, content, page, self.root / 'input.json',
                                           self.root / 'trial.json', self.root / 'filled.pptx',
                                           allow_draft=True, body_header_pilot=False)
            fill.assert_not_called()
        self.assertIsNone(filled)
        self.assertEqual(record['reason_code'], 'TEXT_OVER_CAPACITY')


if __name__ == '__main__':
    unittest.main()
