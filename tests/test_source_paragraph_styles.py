"""Check the opt-in formatting used by reviewed multi-paragraph slots."""
import sys
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fill_layout import write_text_fields


class SourceParagraphStylesTests(unittest.TestCase):
    def test_replacement_keeps_two_paragraphs_and_label_colors(self):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        shape = slide.shapes.add_textbox(0, 0, 127000, 127000)
        first = shape.text_frame.paragraphs[0]
        second = shape.text_frame.add_paragraph()
        source_colors = [['FFFFFF', '002B56'], ['AACCFF', '245612']]
        for paragraph, pair in zip((first, second), source_colors, strict=True):
            for text, rgb, bold in zip(('说明：', '原文'), pair, (True, False), strict=True):
                run = paragraph.add_run()
                run.text = text
                run.font.color.rgb = RGBColor.from_string(rgb)
                run.font.bold = bold
        binding = {'field': 'body', 'shape_id': shape.shape_id, 'preserve_source_text_styles': True}
        replacement = '安排：替换文字\n验收：提交记录'
        write_text_fields({shape.shape_id: shape}, [binding], {'body': replacement}, True)
        self.assertEqual(shape.text, replacement)
        self.assertEqual([[str(run.font.color.rgb) for run in p.runs] for p in shape.text_frame.paragraphs],
                         source_colors)
        self.assertEqual([[run.font.bold for run in p.runs] for p in shape.text_frame.paragraphs],
                         [[True, False], [True, False]])


if __name__ == '__main__':
    unittest.main()
