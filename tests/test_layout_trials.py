import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from layout_trials import infer_relation, trial_alternative
from render_offline_brand import render
from pptx import Presentation


class LayoutTrialTests(unittest.TestCase):
    def setUp(self):
        self.page = {'role': 'body', 'purpose': '工作内容', 'title': '工作内容',
                     'content': {'type': 'cards', 'title': '工作内容', 'items': [
                         {'title': '系统', 'body': '从纸质记录，转向线上记录。'},
                         {'title': '服务', 'body': '从人工受理，转为自助受理。'}]}}

    def test_pairs_reconstruct_every_character_and_keep_order(self):
        relation, layout = infer_relation(self.page, 1)
        self.assertEqual(relation, 'comparison')
        for item, before, after in zip(self.page['content']['items'], layout['left']['body'].splitlines(),
                                       layout['right']['body'].splitlines()):
            self.assertEqual(before + after.removeprefix(item['title'] + '｜'),
                             item['title'] + '｜' + item['body'])
        self.page['content']['items'][1]['body'] = '继续人工受理。'
        self.assertIsNone(infer_relation(self.page, 1))

    def test_rich_or_pinned_content_is_preserved(self):
        self.assertIsNone(infer_relation(dict(self.page, layout_id='pinned'), 1))
        self.page['content']['free_layout'] = {'elements': [{'kind': 'image', 'source_path': 'evidence.png'}]}
        self.assertIsNone(infer_relation(self.page, 1))

    def test_unique_named_goal_and_matching_supports(self):
        content = self.page['content']
        content['items'] = [{'title': label, 'body': label + '说明'} for label in ('设备范围', '交付时限', '系统范围')]
        self.assertEqual(infer_relation(self.page, 7)[1]['lead'], content['items'][1])
        content['items'][0]['title'] = '设备现状'
        self.assertIsNone(infer_relation(self.page, 7))

    def test_actual_render_and_failed_alternative_keeps_original(self):
        choice = {'trial_results': [], 'page': 3}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'page.pptx'
            render({'theme': 'blue', 'complete_deck': False, 'pages': [self.page['content']]}, path)
            self.assertTrue(trial_alternative(self.page, choice, 'original', path, 'blue', repeat=True))
            self.assertEqual(choice['fallback_layout_id'], 'rule_list')
            texts = [s.text for s in Presentation(path).slides[0].shapes if s.has_text_frame]
            self.assertIn(self.page['content']['items'][1]['body'], texts)
            baseline = path.read_bytes()
            self.page['content']['items'][1]['body'] *= 120
            self.assertFalse(trial_alternative(self.page, choice, 'original', path, 'blue', repeat=True))
            self.assertEqual(path.read_bytes(), baseline)
