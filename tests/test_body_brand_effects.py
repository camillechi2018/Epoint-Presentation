import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_deck import audit
from body_background import uses_component_atmosphere
from body_header import frame
from body_layout_recipes import prepare, recipes
from render_offline_brand import PROFILE, add_body_background, add_content_title, read_json, render


class BodyBrandEffectsTests(unittest.TestCase):
    def test_all_registered_rules_draw_editable_body_shapes(self):
        for identifier, rule in recipes()['variants'].items():
            for theme, spec in rule['themes'].items():
                with self.subTest(identifier=identifier, theme=theme), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    deck, plan = root / 'body.pptx', root / 'audit.json'
                    data = {'texts': {field['semantic_path']: f'核对{index}' for index, field
                                     in enumerate(spec['fields'], 1)}}
                    if rule['kind'] == 'metric_evidence':
                        data['texts']['evidence'] = '按原文核对记录。\n登记汇总结果。'
                    images = []
                    for index, item in enumerate(spec['shapes'], 1):
                        if item['kind'] == 'picture':
                            path = root / f'figure-{index}.png'
                            Image.new('RGB', (60, 40), (15 * index, 100, 180)).save(path)
                            images.append({'shape_name': item['name'], 'path': str(path), 'source': '测试生成'})
                    if images:
                        data['images'] = images
                    if rule['kind'] == 'report_table':
                        rows = [['核对条目', '原文依据'], *[[f'条目{i}', f'口径{i}'] for i in range(1, 6)]]
                        data['tables'] = [{'shape_id': 2, 'rows': rows}]
                    prepared = prepare(data, theme, '任务安排', preferred=identifier)
                    render({'theme': theme, 'complete_deck': False, 'pages': [{'title': '任务安排'}]},
                           deck, body_recipe=prepared)
                    plan.write_text(json.dumps({'theme': theme, 'pages': [
                        {'role': 'body', 'selection_mode': 'guided_composition'}]}), encoding='utf-8')
                    self.assertTrue(audit(plan, deck)['p0_passed'])
                    shapes = list(Presentation(deck).slides[0].shapes)
                    by_name = {shape.name: shape for shape in shapes}
                    for item in spec['shapes']:
                        shape = by_name[item['name']]
                        if item['kind'] == 'text':
                            self.assertEqual(shape.text, data['texts'][item['slot']])
                        elif item['kind'] == 'table':
                            self.assertEqual([[cell.text for cell in row.cells] for row in shape.table.rows], rows)
                        elif item['kind'] == 'picture':
                            self.assertEqual(shape.shape_type, MSO_SHAPE_TYPE.PICTURE)
                            original = next(record for record in images if record['shape_name'] == item['name'])
                            self.assertEqual(shape.image.blob, Path(original['path']).read_bytes())
                        if item['kind'] != 'picture':
                            self.assertEqual([shape.left, shape.top, shape.width, shape.height], item['bounds'])

    def test_drawn_long_cards_and_report_tables_keep_editable_evidence(self):
        evidence = '仅纳入统计期内有效记录，按编号去重后汇总。'
        long_evidence = evidence * 3
        items = [{'title': f'指标{i}统计口径与来源说明', 'body': long_evidence} for i in range(5)]
        labels = ['完整口径', '来源', '时间', '检查']
        entries = [long_evidence, '月度记录', '第一季度', '核对编号']
        for theme in ('blue', 'red', 'deep-blue-tech'):
            with self.subTest(theme=theme), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                deck, plan = root / 'slides.pptx', root / 'audit.json'
                pages = [{'type': 'cards', 'title': '长文卡片', 'items': items},
                         {'type': 'report_table', 'title': '条目与依据',
                          'columns': ['条目', '原文依据'], 'row_labels': labels, 'items': entries}]
                render({'theme': theme, 'complete_deck': False, 'pages': pages}, deck)
                slides = Presentation(deck).slides
                text = [shape.text.replace('\n', '') for shape in slides[0].shapes if shape.has_text_frame]
                self.assertEqual(text.count(long_evidence), len(items))
                self.assertTrue(all(item['title'] in text for item in items))
                table, = [shape.table for shape in slides[1].shapes if shape.has_table]
                self.assertEqual([[cell.text for cell in row.cells] for row in table.rows],
                                 [pages[1]['columns'], *map(list, zip(labels, entries, strict=True))])
                self.assertGreater(table.rows[1].height, table.rows[2].height)
                plan.write_text(json.dumps({'theme': theme, 'pages': [
                    {'role': 'body', 'selection_mode': 'guided_composition'} for page in pages]}),
                    encoding='utf-8')
                self.assertTrue(audit(plan, deck)['p0_passed'])

    def test_atmosphere_stays_scoped_to_registered_themes_and_components(self):
        spec = frame()
        for layout in ('content-blue-six-longcopy', 'content-body-gallery-four', 'content-body-gallery-five',
                       'content-body-metric-evidence', 'content-body-report-table'):
            with self.subTest(layout=layout, theme='deep-blue-tech'):
                self.assertFalse(uses_component_atmosphere(spec, layout, 'deep-blue-tech'))
        for theme in ('blue', 'red'):
            with self.subTest(theme=theme):
                self.assertFalse(uses_component_atmosphere(spec, 'content-body-report-table-tech', theme))

    def test_card_background_and_rule_after_template_assembly(self):
        profile = read_json(PROFILE)
        for theme in ('blue', 'red'):
            with self.subTest(theme=theme), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                deck, plan = root / 'cards.pptx', root / 'plan.json'
                pres = Presentation()
                slide = pres.slides.add_slide(pres.slide_layouts[6])
                slide.shapes.add_textbox(0, 0, Inches(1), Inches(1)).text = '正文'
                palette = profile['themes'][theme]
                add_body_background(slide, frame(), theme, palette, palette['canvas'])
                add_content_title(slide, '标题', profile, frame(), palette)
                page = {'role': 'body', 'selection_mode': 'source_template',
                        'layout_id': 'content-body-cards-three-longcopy', 'body_header': {'version': 2}}
                plan.write_text(json.dumps({'theme': theme, 'pages': [page]}), encoding='utf-8')
                pres.save(deck)
                self.assertTrue(audit(plan, deck)['p0_passed'])

                # Reproduce a lost atmosphere layer and an inherited theme shadow.
                ellipse = slide.shapes[1]._element
                ellipse.getparent().remove(ellipse)
                rule = next(shape for shape in slide.shapes if shape.name == 'brand:content-rule')
                rule._element.xpath('./p:style/a:effectRef')[0].set('idx', '1')
                pres.save(deck)
                self.assertEqual({issue['code'] for issue in audit(plan, deck)['issues']},
                                 {'new_drawn_background', 'body_rule_shadow'})
