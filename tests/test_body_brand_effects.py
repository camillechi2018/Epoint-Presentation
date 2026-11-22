import json
import sys
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_deck import audit
from body_header import frame
from render_offline_brand import PROFILE, add_body_background, add_content_title, read_json


class BodyBrandEffectsTests(unittest.TestCase):
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
