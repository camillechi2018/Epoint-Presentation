"""Assemble public headers on pre-extracted editable body components."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

from text_width import visual_width_units

SKILL = Path(__file__).resolve().parents[1]


def body_components_enabled(request):
    return request.get('format', 'pptx') == 'pptx' and request.get('body_header_pilot', True) is True


@lru_cache(maxsize=1)
def frame():
    return json.loads((SKILL / 'assets/layouts/offline-core.json').read_text(encoding='utf-8'))


def contract_for(entry, theme, enabled):
    if (not enabled or theme not in ('blue', 'red', 'deep-blue-tech')
            or entry.get('classification_status') != 'verified'
            or entry.get('role') in ('cover', 'directory', 'section', 'closing')):
        return None
    contract = entry.get('body_component_contract')
    if not isinstance(contract, dict) or contract.get('version') not in (2, 3):
        return None
    themes = contract.get('themes')
    value = themes.get(theme) if isinstance(themes, dict) else None
    if not isinstance(value, dict):
        return None
    if contract['version'] == 3 and theme == 'deep-blue-tech' and value.get('background') != 'skill_tech':
        return None
    return value


def title_path(contract):
    return contract['title_input']['semantic_path']


def frame_spec(contract):
    layout = frame()
    if 'tech' not in contract:
        return layout, 'content_header'
    tech = contract['tech']
    variant, logo = tech['variant'], tech['logo_anchor']
    if variant not in ('standard', 'wide') or logo not in ('top_right', 'bottom_right'):
        raise ValueError('BODY_HEADER_VARIANT_UNSUPPORTED')
    spec = dict(layout['tech_content_header'])
    if variant == 'wide':
        spec['title_box_inches'] = spec['pilot_wide_title_box_inches']
        spec['pilot_title_max_width_units'] = spec['pilot_wide_title_max_width_units']
    if logo == 'bottom_right':
        spec['logo_box_inches'] = spec['pilot_bottom_logo_box_inches']
    return dict(layout, tech_content_header=spec), 'tech_content_header'


def checked_title(binding, texts, page_title, contract):
    path = binding['semantic_path']
    if binding['field'] != path and binding['field'] in texts and path in texts:
        raise ValueError('BODY_HEADER_TITLE_CONFLICT')
    field_title = texts.get(path, texts.get(binding['field']))
    if page_title is not None and field_title is not None and field_title != page_title:
        raise ValueError('BODY_HEADER_TITLE_CONFLICT')
    title = page_title if page_title is not None else field_title
    if not isinstance(title, str) or not title.strip():
        raise ValueError('BODY_HEADER_TITLE_REQUIRED')
    layout, key = frame_spec(contract)
    max_units = layout[key]['pilot_title_max_width_units']
    if len(title.splitlines()) != 1 or '\n' in title or '\r' in title or visual_width_units(title) > max_units:
        raise ValueError('BODY_HEADER_TITLE_OVER_CAPACITY')
    return title


def verify_asset(path, expected_sha):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha:
        raise ValueError('BODY_HEADER_ASSET_HASH_MISMATCH')


def attach_header(presentation, slide, contract, theme, title, logo_enabled):
    from pptx.util import Inches
    from render_offline_brand import PROFILE, add_content_title, add_logo, add_tech_content_header, read_json

    layout, _ = frame_spec(contract)
    canvas = layout['canvas']
    dimensions = (presentation.slide_width, presentation.slide_height)
    expected = (Inches(canvas['width_inches']), Inches(canvas['height_inches']))
    if any(abs(a - b) > 2 for a, b in zip(dimensions, expected)):
        raise ValueError('BODY_HEADER_CANVAS_MISMATCH')
    tech = contract.get('tech')
    if contract.get('background') == 'skill_tech':
        from tech_background import apply_tech_background
        apply_tech_background(slide, layout)
    if tech and not tech.get('omit_art'):
        parent, index = tech_art_placement(slide, tech)
        add_tech_content_header(slide, layout, placement=(parent, index))
    profile = read_json(PROFILE)
    palette = profile['themes'][theme]
    add_content_title(slide, title, profile, layout, palette, tech_header=bool(tech))
    if logo_enabled:
        add_logo(slide, layout, palette, content_header=True, tech_header=bool(tech))
    report = {'frame_id': 'deep-blue-tech-content-header' if tech else 'legacy-blue-red-content-header',
              'version': 2, 'asset': contract['asset'], 'asset_sha256': contract['sha256'],
              'removed_shape_ids': contract['removed_shape_ids']}
    if tech:
        report.update(title_variant=tech['variant'], logo_anchor=tech['logo_anchor'])
    if contract.get('background') == 'skill_tech':
        report.update(version=3, background='skill_tech')
    return report


def tech_art_placement(slide, tech):
    from pptx.enum.shapes import MSO_SHAPE_TYPE as Type

    def locate(shapes, shape_id, kind):
        matches = [shape for shape in shapes if shape.shape_id == shape_id and shape.shape_type == kind]
        if len(matches) != 1:
            raise ValueError(f'BODY_HEADER_OBJECT_MISMATCH: {shape_id}')
        return matches[0]

    if 'art_index' in tech:
        parent = (locate(slide.shapes, tech['root_id'], Type.GROUP)._element
                  if tech.get('root_id') is not None else slide.shapes._spTree)
        return parent, tech['art_index']
    root = locate(slide.shapes, tech['root_id'], Type.GROUP)
    anchor = locate(root.shapes, tech['text_group_id'], Type.GROUP)._element
    return anchor.getparent(), anchor.getparent().index(anchor)
