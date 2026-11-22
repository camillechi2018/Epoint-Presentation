"""Exercise the month-axis contract with editable PowerPoint shapes."""
import sys
import unittest
from pathlib import Path

from pptx import Presentation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from month_schedule import month_ranges, place_month_bars


class MonthScheduleTests(unittest.TestCase):
    def setUp(self):
        presentation = Presentation()
        self.slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        self.months = [
            self.text_box(month * 100000, f'{month}月') for month in range(1, 13)
        ]
        self.first = self.text_box(0, '启动')
        self.last = self.text_box(0, '交付')
        self.rule = {
            'month_header_shape_ids': [shape.shape_id for shape in self.months],
            'bar_shape_ids_by_row': [[self.first.shape_id, self.last.shape_id]],
        }

    def text_box(self, left, text):
        shape = self.slide.shapes.add_textbox(left, 10000, 80000, 15000)
        shape.text = text
        return shape

    def intervals(self, first, last):
        return month_ranges(self.rule, [{'stages': [
            {'start_month': start, 'end_month': end} for start, end in (first, last)
        ]}])

    def test_repositions_single_month_and_multi_month_bars(self):
        receipt = place_month_bars(self.slide, self.rule, self.intervals((2, 2), (10, 12)))
        self.assertTrue(receipt['geometry_bound_to_months'])
        self.assertEqual((self.first.left, self.first.width), (200000, 80000))
        self.assertEqual((self.last.left, self.last.width), (1000000, 280000))
        self.assertEqual((self.last.top, self.last.height, self.last.text), (10000, 15000, '交付'))

    def test_rejects_overlaps_out_of_range_and_boolean_months(self):
        for first, last, code in (
            ((1, 2), (2, 4), 'MONTH_SCHEDULE_OVERLAP'),
            ((1, 2), (10, 13), 'MONTH_SCHEDULE_MONTH_RANGE'),
            ((True, 2), (10, 12), 'MONTH_SCHEDULE_MONTH_RANGE'),
        ):
            with self.subTest(first=first, last=last):
                with self.assertRaisesRegex(ValueError, code):
                    self.intervals(first, last)

    def test_missing_bar_leaves_other_bars_untouched(self):
        intervals = self.intervals((2, 2), (10, 12))
        intervals[-1] = (999, 10, 12)
        with self.assertRaisesRegex(ValueError, 'MONTH_SCHEDULE_BAR_MISSING'):
            place_month_bars(self.slide, self.rule, intervals)
        self.assertEqual((self.first.left, self.first.width), (0, 80000))


if __name__ == '__main__':
    unittest.main()
