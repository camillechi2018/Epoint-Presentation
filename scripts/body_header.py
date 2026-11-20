"""Opt-in title, rule and logo replacement for verified source pages."""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

from text_width import visual_width_units

SKILL = Path(__file__).resolve().parents[1]
PILOT_LAYOUTS = frozenset({'content-blue-112', 'content-blue-244'})


@lru_cache(maxsize=1)
def frame():
    return json.loads((SKILL / 'assets/layouts/offline-core.json').read_text(encoding='utf-8'))


def contract_for(entry, theme, enabled):
    if (not enabled or entry['id'] not in PILOT_LAYOUTS or theme not in ('blue', 'red')
            or entry.get('classification_status') != 'verified'
            or entry.get('role') not in ('summary', 'body', 'content')):
        return None
    contract = entry.get('body_component_contract')
    if not isinstance(contract, dict) or contract.get('version') != 1:
        return None
    themes = contract.get('themes')
    value = themes.get(theme) if isinstance(themes, dict) else None
    return value if isinstance(value, dict) else None


def header_binding(bindings, contract):
    titles = [b for b in bindings if b.get('semantic_path') == 'page.title']
    if (len(titles) != 1 or titles[0]['shape_id'] != contract['title_id']
            or sum(b['shape_id'] == contract['title_id'] for b in bindings) != 1):
        raise ValueError('BODY_HEADER_BINDING_MISMATCH')
    return titles[0]


def checked_title(binding, texts, page_title):
    if binding['field'] in texts and 'page.title' in texts:
        raise ValueError('BODY_HEADER_TITLE_CONFLICT')
    field_title = texts.get('page.title', texts.get(binding['field']))
    if page_title is not None and field_title is not None and field_title != page_title:
        raise ValueError('BODY_HEADER_TITLE_CONFLICT')
    title = page_title if page_title is not None else field_title
    if not isinstance(title, str) or not title.strip():
        raise ValueError('BODY_HEADER_TITLE_REQUIRED')
    max_units = frame()['content_header']['pilot_title_max_width_units']
    if len(title.splitlines()) != 1 or '\n' in title or '\r' in title or visual_width_units(title) > max_units:
        raise ValueError('BODY_HEADER_TITLE_OVER_CAPACITY')
    return title


def verify_source(source, relative, page, contract):
    if relative != contract['source'] or page != contract['page']:
        raise ValueError('BODY_HEADER_SOURCE_MISMATCH')
    digest = hashlib.sha256()
    with source.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != contract['sha256']:
        raise ValueError('BODY_HEADER_SOURCE_MISMATCH')


def replace_header(presentation, slide, contract, theme, title, logo_enabled):
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    from pptx.util import Inches
    from render_offline_brand import PROFILE, add_content_title, add_logo, read_json

    layout = frame()
    canvas = layout['canvas']
    dimensions = (presentation.slide_width, presentation.slide_height)
    expected = (Inches(canvas['width_inches']), Inches(canvas['height_inches']))
    if any(abs(a - b) > 2 for a, b in zip(dimensions, expected)):
        raise ValueError('BODY_HEADER_CANVAS_MISMATCH')
    wanted = {contract['title_id']: MSO_SHAPE_TYPE.TEXT_BOX,
              contract['rule_id']: MSO_SHAPE_TYPE.LINE,
              contract['logo_id']: MSO_SHAPE_TYPE.PICTURE}
    original = [shape for shape in slide.shapes if shape.shape_id in wanted]
    if len(wanted) != 3 or len(original) != 3 or any(
            shape.shape_type != wanted[shape.shape_id] for shape in original):
        raise ValueError('BODY_HEADER_OBJECT_MISMATCH')
    spec = layout['content_header']
    top_limit = Inches(max(spec['title_box_inches'][1] + spec['title_box_inches'][3],
                           spec['logo_box_inches'][1] + spec['logo_box_inches'][3],
                           spec['rule_inches'][1] + spec['rule_width_pt'] / 144))
    for shape in slide.shapes:
        if shape.shape_id in wanted or shape.shape_id in contract.get('nonvisual_ids', ()):
            continue
        angle = math.radians(shape.rotation)
        half_height = (abs(math.sin(angle)) * shape.width + abs(math.cos(angle)) * shape.height) / 2
        if shape.top + shape.height / 2 - half_height < top_limit:
            raise ValueError(f'BODY_HEADER_BODY_COLLISION: {shape.shape_id}')
    for shape in original:
        element = shape._element
        element.getparent().remove(element)
    profile = read_json(PROFILE)
    palette = profile['themes'][theme]
    add_content_title(slide, title, profile, layout, palette)
    if logo_enabled:
        add_logo(slide, layout, palette, content_header=True)
    return {'frame_id': 'legacy-blue-red-content-header', 'version': 1,
            'removed_shape_ids': sorted(wanted), 'source_sha256': contract['sha256']}
