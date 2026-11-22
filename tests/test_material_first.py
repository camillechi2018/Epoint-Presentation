"""Material discovery is driven by evidence and the active catalog, not presentation IDs."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from material_retrieval import MaterialIndex, comparison_facts, coordination_facts


class SourceDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.index=MaterialIndex.__new__(MaterialIndex)
        self.index.entries=[]

    def test_comparison_survives_reordering_and_renaming_catalog(self):
        raw='在办理方面，实现从“纸质收件”“窗口受理”到“在线申请”“电子回执”。\n在反馈方面，实现从“来电”“寄信”到“短信”“平台通知”。'
        self.assertEqual(len(comparison_facts(raw)),2)
        view, _ = self.index.interpret(raw,'parallel-points',2)
        self.assertIsNone(view)
        paths=['items[0].pair.center','items[0].left.first_body','items[0].right.second_body']
        contract={'structure_type':'comparison','required_binding_paths':paths}
        self.index.entries=[({'id':'unrelated-test-id'},contract,[2])]
        view,trace=self.index.interpret(raw,'parallel-points',2)
        self.assertEqual(trace['candidate_ids'],['unrelated-test-id'])
        self.assertEqual(view['items'][1]['right']['second_body'],'平台通知')
        self.assertNotIn('layout_id',view)
        self.assertFalse(comparison_facts(raw.replace('“窗口受理”','')))

    def test_actions_derive_from_source_and_refuse_incomplete_or_negated_facts(self):
        passage='根据物品清单，编制验收表。逐一检查品名、数量，随后向采购方以及保管方报告。最后预订车辆、仓位，完成接收准备。'
        origin, title, rows, end=coordination_facts(passage)
        self.assertEqual((origin,title,end),('物品清单','验收表','完成接收准备'))
        self.assertEqual(rows[1]['tool'],'采购方以及保管方')
        self.assertEqual(rows[2]['tag_b'],'仓位')
        self.assertIsNone(coordination_facts(passage.replace('车辆、仓位','车辆')))
        self.assertIsNone(coordination_facts(passage.replace('预订','不得预订')))

    def test_steps_follow_document_order_with_additional_recipients(self):
        text=('参照申请清单，向财务组、项目组通知；创建记录。'
              '编写审核表，逐项确认金额、期限；'
              '向服务部、运营部备案；预约人力、车辆，完成交接。')
        steps=coordination_facts(text)[2]
        self.assertEqual([s['title'] for s in steps],['通知','编写审核表','备案','预约资源'])
        self.assertIn('创建记录',steps[0]['method'])

    def test_publication_month_is_not_a_project_schedule(self):
        parallel={'structure_type':'parallel-points','required_binding_paths':['items[0].period.month']}
        self.index.entries=[({'id':'calendar-template'},parallel,[3])]
        view,trace=self.index.interpret('5月、6月相继发布政策通知。','parallel-points',3)
        self.assertFalse(trace['candidate_ids'])
        self.assertIsNone(view)
