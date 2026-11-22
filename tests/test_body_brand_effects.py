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
from fill_layout import fill
from render_offline_brand import PROFILE, add_body_background, add_content_title, read_json


class BodyBrandEffectsTests(unittest.TestCase):
    def test_filled_body_components_require_the_shared_background_and_shadowless_rule(self):
        library = Path(__file__).resolve().parents[1] / 'assets' / 'minimal-template-pack'
        layouts = ('content-body-cards-two-longcopy', 'content-body-cards-three-longcopy',
                   'content-body-cards-five-longcopy', 'content-blue-six-longcopy',
                   'content-body-parallel-metrics-two', 'content-body-parallel-metrics-four',
                   'content-body-single-focus', 'content-body-text-hierarchy',
                   'content-body-gallery-four', 'content-body-gallery-five',
                   'content-body-metric-evidence', 'content-body-report-table')
        for layout in layouts:
            for theme in ('blue', 'red'):
                with self.subTest(layout=layout, theme=theme), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    request, deck, plan = root / 'content.json', root / 'cards.pptx', root / 'plan.json'
                    bindings = read_json(library.parent / 'body-components' / 'layouts' / layout
                                         / f'body-{theme}-bindings.json')
                    texts = {field['semantic_path']: f'核对{i}' for i, field in
                             enumerate(bindings['fields'], start=1)}
                    if layout == 'content-body-metric-evidence':
                        texts.update({'metric.value': '96%', 'metric.label': '测试样本核对率',
                                      'metric.period': '本轮测试',
                                      'evidence': '按本轮记录逐项核对样本。\n复查后在汇总表中登记结果。'})
                    data = {'theme': theme, 'texts': texts}
                    images = []
                    for index, slot in enumerate(bindings.get('image_slots', []), start=1):
                        path = root / f'figure-{index}.png'
                        Image.new('RGB', (60, 40), (35 * index, 100, 180)).save(path)
                        images.append({'shape_name': slot['shape_name'], 'path': str(path), 'source': '测试生成'})
                    data['images'] = images
                    table_rows = [['核对条目', '原文依据'], ['测试样本', '按记录逐项核对。'],
                                  ['汇总结果', '按检查表登记。']]
                    if layout == 'content-body-report-table':
                        table_binding, = bindings['objects']['tables']
                        data['tables'] = [{'shape_id': table_binding['shape_id'], 'rows': table_rows}]
                    request.write_text(json.dumps(data), encoding='utf-8')
                    fill(library, layout, request, deck, allow_draft=True, body_header_title='任务安排')
                    page = {'role': 'body', 'selection_mode': 'source_template', 'layout_id': layout,
                            'body_header': {'version': 2}}
                    plan.write_text(json.dumps({'theme': theme, 'pages': [page]}), encoding='utf-8')
                    self.assertTrue(audit(plan, deck)['p0_passed'])

                    pres = Presentation(deck)
                    shapes = pres.slides[0].shapes
                    slide_texts = {shape.text for shape in shapes if shape.has_text_frame}
                    for value in texts.values():
                        self.assertIn(value, slide_texts)
                    picture_blobs = [shape.image.blob for shape in shapes
                                     if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
                    for image in images:
                        self.assertIn(Path(image['path']).read_bytes(), picture_blobs)
                    if layout == 'content-body-report-table':
                        table, = [shape.table for shape in shapes if shape.has_table]
                        self.assertEqual([[cell.text for cell in row.cells] for row in table.rows], table_rows)
                    layers = list(shapes)[:3]
                    self.assertEqual([shape.name for shape in layers],
                                     ['brand:canvas', 'brand:atmosphere:1', 'brand:atmosphere:2'])
                    # A missing second ellipse must block delivery even if the canvas remains.
                    ellipse = layers[-1]._element
                    ellipse.getparent().remove(ellipse)
                    damaged_deck = root / 'damaged.pptx'
                    pres.save(damaged_deck)
                    missing_layer = audit(plan, damaged_deck)
                    self.assertFalse(missing_layer['p0_passed'])
                    self.assertEqual({issue['code'] for issue in missing_layer['issues']}, {'new_drawn_background'})

                    pres = Presentation(deck)
                    rule = next(shape for shape in pres.slides[0].shapes if shape.name == 'brand:content-rule')
                    rule._element.xpath('./p:style/a:effectRef')[0].set('idx', '1')
                    pres.save(damaged_deck)
                    inherited_shadow = audit(plan, damaged_deck)
                    self.assertFalse(inherited_shadow['p0_passed'])
                    self.assertEqual({issue['code'] for issue in inherited_shadow['issues']}, {'body_rule_shadow'})

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
