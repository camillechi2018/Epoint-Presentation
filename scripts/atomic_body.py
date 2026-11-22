"""Select a reviewed fixed-count grouping without discarding supplied body facts."""
from __future__ import annotations

from relation_match import BODY_ROLES, STRUCTURAL_ROLES, is_generic


_INPUT_TYPES = {None, 'atomic_items', 'cards', 'process', 'comparison',
                'schedule', 'metrics', 'timeline', 'milestone_timeline'}
_CONTROL = {'type', 'title', 'relation', 'item_count', 'items', 'page',
            'unit_claims', 'source_refs', 'layout_assessment', 'free_layout',
            'theme', 'library_commit', 'logo', 'variant'}
_HEADINGS = {'heading': 'title', 'title': 'heading'}


def _written(value):
    return isinstance(value, str) and bool(value.strip())


def _metadata(key):
    return key == 'source_refs' or key.endswith('_source_refs')


def _same_value(values):
    if values and all(_written(value) and value == values[0] for value in values):
        return values[0]
    return None


def _relation_keys(page, content):
    values = [page.get('information_relation'), content.get('relation')]
    if not any(_written(value) for value in values):
        values.append(page.get('matching_relation'))
    return {value.strip().casefold() for value in values if _written(value)}


def matches_relation(variant, page, content, taxonomy, *, specified=False):
    keys = _relation_keys(page, content)
    if not keys:
        return specified
    # A canonical structure label alone (for example, “parallel-points”)
    # cannot distinguish similarly shaped components.
    specific = {value for value in keys if not is_generic(value, taxonomy)}
    known = {value.strip().casefold() for value in (variant['relation'], *variant.get('aliases', []))}
    return bool(specific and specific <= known) or (specified and not specific)


def requested(page, content, variants, taxonomy):
    if content.get('type') == 'atomic_items':
        return True
    items = content.get('items')
    if not isinstance(items, list) or not items or content.get('type') not in _INPUT_TYPES:
        return False
    if page.get('layout_id'):
        return False
    fields = {key: value for key, value in content.items() if key != 'item_count'}
    return any(matches_relation(variant, page, content, taxonomy)
               and mapped_texts(dict(variant, count=len(items)), fields, page.get('title')) is not None
               for variant in variants)


def actual_count(page, content):
    items = content.get('items')
    if not isinstance(items, list) or not items:
        raise ValueError('原子变体需要非空 content.items 数组')
    if 'items' in page and page['items'] != items:
        raise ValueError('页面 items 与原子变体 content.items 不一致')
    declared = (page.get('item_count'), (page.get('needs') or {}).get('item_count'), content.get('item_count'))
    if any(value is not None and (type(value) is not int or value != len(items)) for value in declared):
        raise ValueError('指定项数与 content.items 实际数量不一致')
    return len(items)


def _record_fields(record):
    return {key for key in record if not _metadata(key)}


def _item_texts(item, fields, index):
    if not isinstance(item, dict):
        return None
    relevant = _record_fields(item)
    texts = {}
    for field in fields:
        possible = {field}
        alias = _HEADINGS.get(field)
        if alias and alias not in fields:
            possible.add(alias)
        sources = relevant & possible
        value = _same_value([item[key] for key in sorted(sources)])
        if value is None:
            return None
        texts[f'items[{index}].{field}'] = value
        relevant -= sources
    return None if relevant else texts


def mapped_texts(variant, content, page_title):
    """Return a complete binding map only when every content field fits the contract."""
    if content.get('type') not in _INPUT_TYPES:
        return None
    count = variant['count']
    items = content.get('items')
    if not isinstance(items, list) or len(items) != count:
        return None
    if 'item_count' in content and (type(content['item_count']) is not int or content['item_count'] != count):
        return None
    page_fields = set(variant.get('page_fields', []))
    if _record_fields(content) - _CONTROL - page_fields:
        return None
    page = content.get('page', {})
    if not isinstance(page, dict) or _record_fields(page) - {'title'} - page_fields:
        return None
    titles = ([page_title] if page_title is not None else [])
    titles += [record['title'] for record in (content, page) if 'title' in record]
    title = _same_value(titles)
    if title is None:
        return None
    texts = {'page.title': title}
    for field in sorted(page_fields):
        value = _same_value([record[field] for record in (content, page) if field in record])
        if value is None:
            return None
        texts[f'page.{field}'] = value
    for index, item in enumerate(items):
        fields = _item_texts(item, variant['item_fields'], index)
        if fields is None:
            return None
        texts.update(fields)
    return texts


def prepared_texts(variant, content):
    """Validate a caller's explicit fixed-count semantic binding request."""
    if content.get('type') != 'template_fields':
        return False
    if _record_fields(content) - _CONTROL - {'texts'} or 'items' in content or 'page' in content:
        return False
    if 'item_count' in content and (type(content['item_count']) is not int
                                    or content['item_count'] != variant['count']):
        return False
    expected = {'page.title'} | {f'page.{field}' for field in variant.get('page_fields', [])}
    expected |= {f'items[{i}].{field}' for i in range(variant['count']) for field in variant['item_fields']}
    texts = content.get('texts')
    return isinstance(texts, dict) and texts.keys() == expected and all(_written(v) for v in texts.values())


def eligibility(variant, entry, page, content, taxonomy, *, specified):
    requested_role = page.get('role')
    if requested_role in STRUCTURAL_ROLES or (requested_role not in BODY_ROLES
            and requested_role not in (None, entry.get('role'))):
        return 'role'
    if not matches_relation(variant, page, content, taxonomy, specified=specified):
        return 'atomic_relation'
    items = content.get('items')
    if isinstance(items, list):
        if len(items) != variant['count']:
            return 'item_count_unverified'
        if mapped_texts(variant, content, page.get('title')) is not None:
            return None
    elif specified and prepared_texts(variant, content):
        return None
    return 'atomic_fields'


def trace(entry):
    variant = entry.get('atomic_variant')
    if not variant:
        return {}
    return {'atomic_variant': {key: variant[key] for key in ('parent_id', 'count', 'relation')}}


def _body_text(value):
    if isinstance(value, str):
        return value
    if type(value) in (int, float):
        return str(value)
    if isinstance(value, bool):
        return '是' if value else '否'
    if isinstance(value, list):
        return '、'.join(_body_text(item) for item in value)
    if isinstance(value, dict):
        return _record_text(value)
    raise ValueError('原子变体托底只能排版已有文字；请使用能完整承载内容的版式')


def _record_text(record):
    return '｜'.join(f'{key}：{_body_text(value)}' for key, value in record.items()
                    if not _metadata(key) and value is not None)


def fallback_content(content, page_title):
    """Use an editable list if no reviewed variant can carry all facts."""
    if 'logo' in content:
        raise ValueError('原子变体托底须保留所给 Logo，请使用支持该 Logo 的版式')
    page = content.get('page') or {}
    if not isinstance(page, dict):
        raise ValueError('原子变体 page 必须是对象')
    title = page_title or content.get('title') or page.get('title')
    supplied = {key: value for key, value in content.items() if key not in _CONTROL}
    groups = [{key: value for key, value in page.items() if key != 'title'}, supplied]
    alternate_titles = [value for value in (content.get('title'), page.get('title'))
                        if _written(value) and value != title]
    rows = list(dict.fromkeys(alternate_titles + [_record_text(group) for group in groups if group]))
    rows.extend(_record_text(item) if isinstance(item, dict) else _body_text(item)
                for item in content['items'])
    return {'type': 'bullets', 'title': title, 'items': [row for row in rows if row]}
