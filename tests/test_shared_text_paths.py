"""Exercise one semantic value written to multiple native text fields."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fill_layout import expand_shared_text_paths


class SharedTextPathsTests(unittest.TestCase):
    @staticmethod
    def bindings():
        return [{'semantic_path':'items[0].heading','field':'navigation'},
                {'semantic_path':'items[0].heading','field':'card'},
                {'semantic_path':'items[0].body','field':'body'}]

    def test_one_semantic_value_fills_both_edited_positions(self):
        texts = {'card':'提交验收','body':'确认反馈'}
        expand_shared_text_paths(texts,self.bindings(),['items[0].heading'])
        self.assertEqual(texts,{'navigation':'提交验收','card':'提交验收','body':'确认反馈'})

    def test_rejects_inconsistent_values_in_native_slots(self):
        texts = {'navigation':'材料核对','card':'提交验收'}
        with self.assertRaisesRegex(ValueError,'共享文字字段的内容不一致'):
            expand_shared_text_paths(texts,self.bindings(),['items[0].heading'])
