"""Prepare and bind galleries, sourced metrics and single-focus body pages."""
from pathlib import Path
import re

from relation_match import STRUCTURAL_ROLES


BODY_RELATIONS = {
    'image_gallery': 'image-text',
    'metric_evidence': 'metrics',
    'single_focus': 'single-focus',
}
RELATIONS = {kind: {relation} for kind, relation in BODY_RELATIONS.items()}
RELATIONS['metric_evidence'].add('data')
_CONTEXT = {'type', 'title', 'unit_claims', 'source_refs', 'logo', 'theme', 'library_commit'}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _only_fields(record, allowed):
    return isinstance(record, dict) and record.keys() <= allowed


def _metric_is_sourced(metric, paragraphs, source_refs):
    if (not _only_fields(metric, {'label', 'value', 'period', 'evidence_index'})
            or not _text(metric.get('label')) or not _text(metric.get('value'))
            or not isinstance(source_refs, list) or not any(_text(ref) for ref in source_refs)
            or not any(char.isdecimal() for char in metric['value'])):
        return False
    index = metric.get('evidence_index')
    if type(index) is not int or not 0 <= index < len(paragraphs):
        return False
    support = paragraphs[index]
    value = re.escape(metric['value'])
    return (metric['label'] in support and re.search(r'(?<![\d.])' + value + r'(?![\d.])', support) is not None
            and ('period' not in metric or (_text(metric['period']) and metric['period'] in support)))


def _gallery_pairs(content):
    layout = content.get('free_layout')
    elements = layout.get('elements') if isinstance(layout, dict) else None
    if (content.get('type') != 'free_composition' or not _only_fields(layout, {'rationale', 'elements'})
            or not isinstance(elements, list)
            or len(elements) not in (8, 10)):
        return None
    pairs = []
    for picture, caption in zip(elements[::2], elements[1::2], strict=True):
        if (not _only_fields(picture, {'kind', 'x', 'y', 'w', 'h', 'source_path'})
                or picture.get('kind') != 'image' or not _text(picture.get('source_path'))
                or not _only_fields(caption, {'kind', 'x', 'y', 'w', 'h', 'text', 'size_pt',
                                              'color_role', 'font_role', 'bold', 'align'})
                or caption.get('kind') != 'text' or not _text(caption.get('text'))):
            return None
        if (not all(type(item.get(key)) in (int, float) for item in (picture, caption)
                    for key in ('x', 'y', 'w', 'h'))
                or picture['x'] != caption['x'] or picture['w'] != caption['w']
                or caption['y'] < picture['y'] + picture['h']):
            return None
        pairs.append({'image_path': picture['source_path'], 'caption': caption['text']})
    return pairs


def matching_content(page):
    """Add a source-proven matching interpretation while keeping fallback content intact."""
    original = page.get('content') or {}
    annotation = page.get('body_match')
    if annotation is None or page.get('role') in STRUCTURAL_ROLES:
        kind = original.get('type') if isinstance(original, dict) else None
        if isinstance(kind, str) and kind in BODY_RELATIONS and 'source_refs' in page:
            return dict(original, source_refs=original.get('source_refs', page['source_refs'])), None
        return original, None
    kind = annotation.get('type') if isinstance(annotation, dict) else None
    label = kind if isinstance(kind, str) and kind in BODY_RELATIONS else 'invalid'
    rejected = original, f'body_match_rejected:{label}'
    relation = page.get('matching_relation') or page.get('information_relation')
    if (label == 'invalid' or relation not in RELATIONS[kind]
            or not isinstance(original, dict)):
        return rejected

    context = {key: value for key, value in original.items() if key in _CONTEXT}
    context['type'] = kind
    if kind == 'image_gallery':
        if (not _only_fields(annotation, {'type'})
                or not _only_fields(original, _CONTEXT | {'layout_assessment', 'free_layout'})):
            return rejected
        items = _gallery_pairs(original)
        if items is None:
            return rejected
        context['items'] = items
    else:
        items = original.get('items')
        if (original.get('type') != 'bullets' or not _only_fields(original, _CONTEXT | {'items'})
                or not isinstance(items, list) or not all(_text(item) for item in items)):
            return rejected
        context['items'] = items
        if kind == 'single_focus':
            index = annotation.get('thesis_index')
            if (not _only_fields(annotation, {'type', 'thesis_index'}) or len(items) != 3
                    or type(index) is not int or not 0 <= index < len(items)):
                return rejected
            context['thesis_index'] = index
        else:
            metric = annotation.get('metric')
            refs = page.get('source_refs', original.get('source_refs'))
            if not _only_fields(annotation, {'type', 'metric'}) or not _metric_is_sourced(metric, items, refs):
                return rejected
            context.update(metric=metric, source_refs=refs)
    return context, f'body_match:{kind}'


def adapt_body_input(contract, content, page_title):
    """Validate the typed payload and map it to its reviewed native PowerPoint slots."""
    kind = contract.get('body_input')
    title = content.get('title') or page_title
    items = content.get('items')
    rejected = dict(content), None
    if (not isinstance(kind, str) or kind not in BODY_RELATIONS or content.get('type') != kind or not _text(title)
            or not isinstance(items, list) or len(items) not in contract.get('verified_counts', [])):
        return rejected
    texts = {'page.title': title}
    images = []
    if kind == 'image_gallery':
        slots = contract.get('image_slots', [])
        if len(slots) != len(items) or not _only_fields(content, _CONTEXT | {'items'}):
            return rejected
        for slot, item in zip(slots, items, strict=True):
            if (not _only_fields(item, {'image_path', 'caption'}) or not _text(item.get('caption'))
                    or not _text(item.get('image_path'))):
                return rejected
            path = Path(item['image_path'])
            if not path.is_absolute() or path.suffix.lower() not in {'.jpg', '.jpeg', '.png'} or not path.is_file():
                return rejected
            images.append({'shape_name': slot['shape_name'], 'path': str(path), 'source': str(path)})
            texts[slot['semantic_path']] = item['caption']
    else:
        if not all(_text(item) for item in items):
            return rejected
        if kind == 'metric_evidence':
            metric = content.get('metric')
            if (not _only_fields(content, _CONTEXT | {'items', 'metric'})
                    or not _metric_is_sourced(metric, items, content.get('source_refs'))):
                return rejected
            texts.update({f'metric.{key}': metric[key] for key in ('label', 'value', 'period') if key in metric})
            texts['evidence'] = '\n'.join(items)
        else:
            index = content.get('thesis_index')
            if (not _only_fields(content, _CONTEXT | {'items', 'thesis_index'}) or len(items) != 3
                    or type(index) is not int or not 0 <= index < len(items)):
                return rejected
            texts['thesis'] = items[index]
            for slot, evidence in enumerate(items[:index] + items[index + 1:]):
                texts[f'items[{slot}].body'] = evidence
    result = dict(content, texts=texts)
    if images:
        result['images'] = images
    return result, f'{kind}_to_fields'
