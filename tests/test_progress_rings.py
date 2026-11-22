"""Keep native progress geometry and a single-line percentage in sync."""
import sys
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from progress_rings import apply_progress_rings, progress_percentage


class ProgressRingTests(unittest.TestCase):
    def test_full_progress_uses_a_single_line_and_an_unfilled_ellipse(self):
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        arc = slide.shapes.add_shape(MSO_SHAPE.ARC, 0, 0, 500000, 500000)
        arc.adjustments[0] = 0.75
        arc.adjustments[1] = 0.25
        label = slide.shapes.add_textbox(100000, 200000, 300000, 100000)
        label.text = '100%'
        label.text_frame.word_wrap = True
        rule = {'arc_shape_id': arc.shape_id, 'text_shape_id': label.shape_id,
                'value_field': 'items[0].progress.value'}
        shapes = {shape.shape_id: shape for shape in slide.shapes}
        result = apply_progress_rings(shapes, [rule], {'field': label.text}, {rule['value_field']: 'field'})

        self.assertEqual(result[0]['sweep_angle_units'], 360 * 60000)
        self.assertIs(label.text_frame.word_wrap, False)
        self.assertEqual(label.text, '100%')
        self.assertEqual(arc._element.spPr.xpath('a:prstGeom')[0].get('prst'), 'ellipse')
        self.assertTrue(arc._element.spPr.xpath('a:noFill'))

    def test_rejects_invalid_percentages(self):
        for value in ('101%', '10.5%', '-1%', '70'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'PROGRESS_RING_PERCENTAGE'):
                progress_percentage(value)
