import os
import json
import sys
import tempfile
import unittest
from pathlib import Path

LIBRARY = Path(os.environ.get('EPOINT_TEST_LIBRARY', str(Path(__file__).resolve().parents[1] / '.test-library-required')))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from capacity_preflight import preflight, _safe_wrap
from content_adapters import adapt_for_layout
from fill_layout import fill
from plan_deck import resolve


class CapacityPreflightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads((LIBRARY / 'catalog.json').read_text(encoding='utf-8'))
        cls.entries = {entry['id']: entry for entry in catalog['layouts']}

    def test_three_line_wrap_keeps_clauses_and_original_text(self):
        source = ('第一阶段完成资料核对，共整理十二份文件；'
                  '第二阶段开展现场验收，共覆盖三个部门；'
                  '第三阶段核实问题清单，并记录后续安排。')
        wrapped = _safe_wrap(source, 45, 3, len(source) + 2, prefer_three=True)
        self.assertEqual(wrapped.replace('\n', ''), source)
        self.assertEqual(wrapped.count('\n'), 2)
        self.assertTrue(wrapped.split('\n')[0].endswith('；'))
        self.assertTrue(wrapped.split('\n')[1].endswith('；'))
        self.assertIsNone(_safe_wrap(source, 45, 3, len(source), prefer_three=True))

    def test_wrap_does_not_split_decimal_number(self):
        source = ('本月投入31.34万元，环比增长6.12%；'
                  '第一组核对合同，第二组核对项目成本。')
        wrapped = _safe_wrap(source, 27, 3, len(source) + 2, prefer_three=True)
        self.assertIsNotNone(wrapped)
        self.assertEqual(wrapped.replace('\n', ''), source)
        self.assertNotIn('31.\n34', wrapped)
        self.assertNotIn('6.\n12', wrapped)

    def test_wrap_keeps_number_and_chinese_unit_together(self):
        source = ('甲方团队（123456）成立于2020年，设12大区域服务组；'
                  '项目服务覆盖规划、研发、交付与运营。')
        wrapped = _safe_wrap(source, 36, 3, len(source) + 2, prefer_three=True)
        self.assertEqual(wrapped.replace('\n', ''), source)
        self.assertIn('）\n成立', wrapped)
        self.assertNotIn('12\n大', wrapped)
        self.assertNotIn('2020\n年', wrapped)

    def test_known_p142_center_title_wrap_preserves_text_and_fills(self):
        entry = self.entries['content-blue-142']
        content = {'type': 'cards', 'center': {'title': '服务能力'},
                   'items': [{'title': f'项目{i}', 'body': '说明'} for i in range(4)]}
        check = preflight(LIBRARY, entry, content, '业务概览', 'blue')
        self.assertEqual(check['status'], 'wrap_possible')
        wrapped = check['wrap_suggestions']['center.title']
        self.assertEqual(wrapped.replace('\n', ''), '服务能力')
        self.assertTrue(check['longcopy_sha256'])
        mapped, adapter = adapt_for_layout(entry['id'], content, '业务概览', entry=entry)
        self.assertIsNotNone(adapter)
        mapped['texts']['center.title'] = wrapped
        mapped['theme'] = 'blue'
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.json'
            output = Path(directory) / 'page.pptx'
            source.write_text(json.dumps(mapped, ensure_ascii=False), encoding='utf-8')
            fill(LIBRARY, entry['id'], source, output, allow_draft=True)
            self.assertGreater(output.stat().st_size, 1000)

    def test_body_wrap_without_clause_boundary_requests_review(self):
        entry = self.entries['content-blue-106']
        content = {'type': 'cards', 'items': [
            {'title': '报名', 'body': '提前确认可参与的日期和时段。'},
            {'title': '分工', 'body': '按现场人数分配引导与记录。'},
            {'title': '培训', 'body': '活动前说明路线及求助方式。'},
            {'title': '服务', 'body': '现场记录需求并及时移交。'},
            {'title': '回访', 'body': '整理反馈，明确下次调整事项。'}]}
        check = preflight(LIBRARY, entry, content, '社区志愿', 'blue')
        self.assertEqual(check['status'], 'wrap_possible')
        risks = {item['field'] for item in check['advisory']
                 if item['rule'] == 'mid_phrase_wrap_review'}
        self.assertIn('items[0].body', risks)
        self.assertIn('items[2].body', risks)
        self.assertNotIn('items[4].body', risks)

    def test_real_customer_copy_ranks_roomier_card_before_tight_card(self):
        content = {'type': 'cards', 'items': [
            {'title': '产品体验', 'body': '通过持续维护、优化搜索引擎词库，让用户搜的更快、更准'},
            {'title': '商品扩充', 'body': '可售类目内的商品是否可直接上架？'},
            {'title': '社群宣传', 'body': '发布宣传海报有哪些内容上的限制以及要求？'},
            {'title': '线下宣传', 'body': '是否允许此类线下推广方式？'}]}
        request = {'theme': 'blue', 'asset_policy': 'verified_draft', 'allow_draft': True,
                   'pages': [{'role': 'body', 'purpose': '运营计划与待确认事项',
                              'title': '运营计划与待确认事项', 'content': content}]}
        result = resolve(LIBRARY, request)['pages'][0]
        self.assertEqual(result['candidate_ids'][0], 'content-blue-112')
        summaries = {row['layout_id']: row for row in result['candidate_summaries']}
        self.assertGreater(len(summaries['content-blue-143']['capacity_preflight']['advisory']),
                           len(summaries['content-blue-112']['capacity_preflight']['advisory']))


if __name__ == '__main__':
    unittest.main()
