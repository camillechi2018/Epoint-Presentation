"""Verify inclusive period mapping for a native bar and its separate label."""
import sys
import unittest
from pathlib import Path

from pptx import Presentation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from period_schedule import place_period_bars, schedule_intervals


class PeriodScheduleTests(unittest.TestCase):
    def test_grouped_span_repositions_existing_shapes(self):
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        months = [slide.shapes.add_textbox(i*100000,0,85000,30000) for i in range(12)]
        for number,header in enumerate(months,1):
            header.text = f'{number}月'
        bar = slide.shapes.add_textbox(0,80000,1000,30000)
        label = slide.shapes.add_textbox(0,80000,1000,30000)
        label.text = '联调'
        schedule = {'unit':'month','header_ids':[m.shape_id for m in months],
                    'rows':[{'item':0,'task':0,'stages':[{'bar_id':bar.shape_id,'label_id':label.shape_id}]}]}
        items = [{'tasks':[{'stages':[{'start_month':3,'end_month':5,'label':label.text}]}]}]
        intervals = schedule_intervals(schedule,items)
        receipt = place_period_bars(slide,schedule,intervals)
        self.assertTrue(receipt['geometry_bound_to_periods'])
        self.assertEqual((bar.left,bar.width),(200000,285000))
        self.assertEqual((label.left,label.width,label.top,label.text),(200000,285000,80000,'联调'))

    def test_disallows_overlapping_intervals_on_one_task(self):
        rule = {'unit':'quarter','rows':[{'item':0,'task':None,'stages':[{},{}]}]}
        items = [{'stages':[{'start_quarter':1,'end_quarter':2},{'start_quarter':2,'end_quarter':4}]}]
        with self.assertRaisesRegex(ValueError,'PERIOD_SCHEDULE_OVERLAP'):
            schedule_intervals(rule,items)
