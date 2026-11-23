"""Generate the legacy body design variants as editable PowerPoint objects."""
import json
from functools import lru_cache
from pathlib import Path

from body_header import frame_spec, title_fits_frame
from capacity_preflight import wrap_card_body
from content_adapters import adapt_body_input, matching_content, unmapped_title_body_fields
from text_width import binding_text_issues


RULES = Path(__file__).resolve().parents[1] / 'assets/layouts/body-variants.json'


@lru_cache(maxsize=1)
def recipes():
    return json.loads(RULES.read_text(encoding='utf-8'))


def page_content(page):
    interpreted, source = matching_content(page)
    if (source or '').startswith('body_match:'):
        return interpreted
    content = page.get('content') or {}
    if 'source_refs' in page and 'source_refs' not in content:
        return dict(content, source_refs=page['source_refs'])
    return content


def _typed_values(recipe, content, title):
    kind = recipe['kind']
    contract = recipe['contract']
    if kind != 'cards':
        mapped, adapter = adapt_body_input(contract, content, title)
        return mapped if adapter else None
    items = content.get('items')
    if (not isinstance(items, list) or len(items) not in contract['verified_counts']
            or unmapped_title_body_fields(content)):
        return None
    texts = {}
    for item, paths in zip(items, contract['title_body_fields']['items'], strict=True):
        if not isinstance(item, dict):
            return None
        texts.update({path: item.get(name) for name, path in paths.items()})
    return {'texts': texts}


def _prepared_values(frame, content):
    fields = content.get('texts')
    if not isinstance(fields, dict):
        return None
    if set(content) - {'type', 'title', 'texts', 'images', 'tables', 'theme', 'library_commit',
                       'source_refs', 'data_source', 'unit_claims'}:
        return None
    aliases = {field['field']: field['semantic_path'] for field in frame['fields']}
    aliases[frame['title_alias']] = 'page.title'
    allowed = set(aliases.values())
    texts = {}
    for key, value in fields.items():
        path = aliases.get(key, key)
        if path not in allowed or (path in texts and texts[path] != value):
            return None
        texts[path] = value
    return dict(content, texts=texts)


def prepare(content, theme, title=None, *, preferred=None):
    """Return drawing data when the theme, content and verified slot limits fit."""
    variants = recipes()['variants']
    identifiers = [preferred] if preferred else variants
    kind = content.get('type')
    title = content.get('title') or title
    if preferred is None and (kind == 'cards' and content.get('variant', 'auto') != 'auto'):
        return None
    for identifier in identifiers:
        recipe = variants.get(identifier, {})
        frame = recipe.get('themes', {}).get(theme)
        if not frame or (not preferred and recipe['kind'] != kind):
            continue
        mapped = _typed_values(recipe, content, title) if kind == recipe['kind'] else None
        if not mapped and preferred:
            mapped = _prepared_values(frame, content)
        if not mapped:
            continue
        texts = dict(mapped['texts'])
        field_title = texts.pop('page.title', None)
        if preferred and field_title and title and title != field_title:
            continue
        actual_title = title or field_title
        dimensions, key = frame_spec(frame['header'])
        if not title_fits_frame(actual_title, dimensions[key]):
            continue
        if not _validate_texts(recipe, frame, texts):
            continue
        images = mapped.get('images', [])
        tables = mapped.get('tables', [])
        if not _validate_objects(frame, recipe['contract'], images, tables):
            continue
        return {'id': identifier, 'type': recipe['kind'], 'frame': frame, 'title': actual_title,
                'texts': texts, 'images': {img['shape_name']: Path(img['path']) for img in images},
                'rows': tables[0]['rows'] if tables else None}
    if preferred:
        raise ValueError(f'版式规则 {preferred} 的主题、字段或容量与本页内容不匹配')
    return None


def _validate_texts(recipe, frame, texts):
    if recipe['kind'] == 'metric_evidence':
        evidence = texts.get('evidence')
        lines = evidence.splitlines() if isinstance(evidence, str) else []
        if len(lines) not in recipe['contract']['verified_counts'] or not all(line.strip() for line in lines):
            return False
    for field in frame['fields']:
        path = field['semantic_path']
        value = texts.get(path)
        if not field.get('required', True) and (value is None or isinstance(value, str) and not value.strip()):
            texts.pop(path, None)
            continue
        if not isinstance(value, str) or not value.strip():
            return False
        if (width := recipe.get('wrap_width')) and path.endswith('.body'):
            value = wrap_card_body(value, width, field['max_lines'])
        if value is None or binding_text_issues(value, field):
            return False
        texts[path] = value
    return True


def _validate_objects(frame, contract, images, tables):
    needed = {shape['name'] for shape in frame['shapes'] if shape['kind'] == 'picture'}
    if (not isinstance(images, list) or len(images) != len(needed)
            or not all(isinstance(img, dict) and img.get('shape_name') in needed
                       and isinstance(img.get('path'), str) and Path(img['path']).is_file()
                       and isinstance(img.get('source'), str) and img['source'].strip() for img in images)
            or len({img['shape_name'] for img in images}) != len(needed)):
        return False
    table = next((shape for shape in frame['shapes'] if shape['kind'] == 'table'), None)
    if table is None:
        return not tables
    if not isinstance(tables, list) or len(tables) != 1 or not isinstance(tables[0], dict):
        return False
    rows = tables[0].get('rows')
    return (tables[0].get('shape_id') == contract['table_shape_id']
            and isinstance(rows, list) and 1 <= len(rows) <= len(table['rows'])
            and all(isinstance(row, list) and len(row) == len(table['columns'])
                    and all(isinstance(cell, str) and len(cell) <= 100 for cell in row) for row in rows))


def _style_element(spec):
    from pptx.oxml.xmlchemy import OxmlElement

    node = OxmlElement(spec[0])
    if len(spec) > 1:
        for key, value in spec[1].items():
            node.set(key, value)
    if len(spec) > 2:
        node.extend(_style_element(child) for child in spec[2])
    return node


def _write_text(frame, value, spec, *, regular=False):
    body = frame._txBody
    body.replace(body.bodyPr, _style_element(spec[0]))
    frame.text = value
    for paragraph in frame.paragraphs:
        properties = _style_element(spec[1])
        properties.set('hangingPunct', '0')
        properties.set('eaLnBrk', '1')
        paragraph._p.replace(paragraph._p.get_or_add_pPr(), properties)
        if len(spec) > 2:
            for run in paragraph.runs:
                run._r.insert(0, _style_element(spec[2]))
        if regular:
            for run in paragraph.runs:
                run.font.bold = False


def draw(slide, prepared):
    """Use shared styling tokens to draw primitives, text, images and native tables."""
    from PIL import Image
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.oxml.ns import qn

    style_bank = recipes()['styles']
    recipe = recipes()['variants'][prepared['id']]
    regular = {field['semantic_path'] for field in prepared['frame']['fields']
               if field.get('semantic_role') in recipe.get('regular_text_roles', [])}
    for item in prepared['frame']['shapes']:
        kind = item['kind']
        x, y, w, h = item['bounds']
        if kind == 'picture':
            path = prepared['images'][item['name']]
            with Image.open(path) as image:
                iw, ih = image.size
            scale = min(w / iw, h / ih)
            pw, ph = int(iw * scale), int(ih * scale)
            shape = slide.shapes.add_picture(str(path), x + (w - pw) // 2, y + (h - ph) // 2, pw, ph)
        elif kind == 'table':
            rows = prepared['rows']
            shape = slide.shapes.add_table(len(rows), len(item['columns']), x, y, w, h)
            table = shape.table
            properties = table._tbl.find(qn('a:tblPr'))
            properties.attrib.clear()
            properties.find(qn('a:tableStyleId')).text = item['table_style']
            for col, width in zip(table.columns, item['columns'], strict=True):
                col.width = width
            for row_index, values in enumerate(rows):
                table.rows[row_index].height = item['rows'][row_index]
                for col_index, value in enumerate(values):
                    cell = table.cell(row_index, col_index)
                    text_style, cell_style = item['cells'][row_index][col_index]
                    cell._tc.replace(cell._tc.get_or_add_tcPr(), _style_element(style_bank[cell_style][0]))
                    _write_text(cell.text_frame, value, style_bank[text_style])
        elif kind == 'text':
            shape = slide.shapes.add_textbox(x, y, w, h)
            slot = item['slot']
            _write_text(shape.text_frame, prepared['texts'].get(slot, ''), style_bank[item['style']],
                        regular=slot in regular)
        else:
            geometry = MSO_SHAPE.RECTANGLE if item['geometry'] == 'rect' else MSO_SHAPE.ROUNDED_RECTANGLE
            shape = slide.shapes.add_shape(geometry, x, y, w, h)
            properties = shape._element.spPr
            for node in list(properties):
                if node.tag != qn('a:xfrm'):
                    properties.remove(node)
            properties.extend(_style_element(spec) for spec in style_bank[item['style']])
        shape.name = item['name']
