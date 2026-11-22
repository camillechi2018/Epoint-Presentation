"""Lossless relation interpretations and guided alternatives for editable body slides."""
import re
from collections import Counter

from fallback_rules import uses_minimal_body_layout


def automatic_body(page):
    content = page.get('content') or {}
    return (page.get('role') in (None, 'body', 'content', 'parallel', 'summary')
            and not page.get('layout_id')
            and content.get('variant') in (None, 'auto')
            and not uses_minimal_body_layout(content.get('type'), content.get('variant'))
            and not content.get('layout_assessment') and not content.get('keep_bullets_reason'))


def plain_items(content):
    """A free fallback may duplicate the payload, but may also contain unique evidence."""
    if set(content) - {'type', 'title', 'items', 'variant', 'free_layout'}:
        return None
    items = content.get('items')
    if not isinstance(items, list) or not items or not all(
        isinstance(item, dict) and set(item) == {'title', 'body'}
        and all(isinstance(value, str) and value.strip() for value in item.values()) for item in items
    ):
        return None
    facts = {value for item in items for value in item.values()} | {content.get('title')}
    for element in content.get('free_layout', {}).get('elements', []):
        if element.get('kind') != 'text':
            return None
        text = element.get('text', '')
        if text not in facts and text not in {f'{i:02d}' for i in range(1, len(items) + 1)}:
            return None
    return items


def infer_relation(page, number):
    """Only reinterpret generic cards when every row explicitly supports the relation."""
    content = page['content']
    if (not automatic_body(page) or page.get('body_match') or page.get('matching_relation')
            or content.get('type') != 'cards'):
        return None
    if page.get('information_relation') not in (None, 'parallel-points', 'summary', 'framework'):
        return None
    items = plain_items(content)
    if not items or len(items) < 2 or ('items' in page and page['items'] != items):
        return None
    title = page.get('title') or content.get('title')
    if content.get('title', title) != title:
        return None
    pairs = [re.fullmatch(r'(从[^，。；]+[，,])((?:转向|转为|变为|转变为).+)', item['body']) for item in items]
    if all(pairs):
        candidate = {'type': 'comparison', 'title': title}
        for side, heading, group in [('left', '变化前', 1), ('right', '变化后', 2)]:
            lines = [item['title'] + '｜' + pair[group] for item, pair in zip(items, pairs)]
            candidate[side] = {'title': heading, 'body': '\n'.join(lines)}
        relation = 'comparison'
    else:
        leads = [i for i, item in enumerate(items) if re.fullmatch(
            r'(?:总体|核心|主要|交付|建设|项目)?(?:目标|时限|期限)', item['title'])]
        if len(leads) != 1 or len(items) < 3:
            return None
        lead = leads[0]
        support = [item for i, item in enumerate(items) if i != lead]
        if not all(re.search(r'(范围|任务|举措|措施|工作包)$', item['title']) for item in support):
            return None
        candidate = {'type': 'priority_grid', 'variant': 'summary_split', 'title': title,
                     'lead': items[lead], 'support': support}
        relation = 'single-focus'
    from render_offline_brand import validate_page
    try:
        validate_page(candidate, number)
    except ValueError:
        return None
    return relation, candidate


def layout_key(choice):
    if choice['selection_mode'] == 'source_template':
        return choice.get('layout_id')
    if choice['selection_mode'] == 'guided_composition':
        return (choice.get('fallback_layout_id'), choice.get('variant'))
    return None


def guided_alternatives(content, *, repeat):
    kind = content.get('type')
    if kind in ('cards', 'process') and plain_items(content):
        base = {key: content[key] for key in ('title', 'items') if key in content}
        if kind == 'cards':
            yield dict(base, type='rule_list')
            if repeat:
                yield dict(base, type='cards', variant='grid')
        if kind == 'process':
            yield dict(base, type='process', variant='open_steps')
            if repeat:
                yield dict(base, type='process', variant='rail')
                # Rule-list rows carry editable step numbers in source order.
                yield dict(base, type='rule_list')
    elif repeat and kind == 'bullets' and all(isinstance(x, str) for x in content.get('items', [])):
        for variant in ('balanced', 'spacious', 'compact'):
            yield dict(content, variant=variant)
    elif repeat and kind in ('priority_grid', 'milestone_timeline'):
        variants = ('side', 'top', 'summary_split') if kind == 'priority_grid' else ('horizontal', 'vertical')
        for variant in variants:
            yield dict(content, variant=variant)
    if repeat and kind and not uses_minimal_body_layout(kind, content.get('variant')):
        yield dict(content)


def text_fields(value):
    if isinstance(value, dict):
        for key, field in value.items():
            if key not in ('type', 'variant', 'free_layout', 'layout_assessment'):
                yield from text_fields(field)
    elif isinstance(value, list):
        for field in value:
            yield from text_fields(field)
    elif isinstance(value, (int, float, str)) and not isinstance(value, bool):
        yield str(value)


def retains_text(path, required):
    from pptx import Presentation
    from layout_safety import walk_shapes
    texts = []
    for shape in walk_shapes(Presentation(path).slides[0].shapes):
        if shape.has_text_frame:
            texts.append(shape.text)
        elif shape.has_table:
            texts.extend(cell.text for cell in shape.table.iter_cells())
    # Layout-generated breaks may split one field. Never join unrelated shapes.
    def normal(value):
        return re.sub(r'[\r\n\v]', '', value)

    available = [normal(s) for s in texts]
    return all(sum(s.count(field) for s in available) >= count
               for field, count in Counter(normal(s) for s in required if s.strip()).items())


def trial_alternative(page, choice, previous, path, theme, *, repeat):
    """Render on a separate path. Keep the original slide until all checks pass."""
    from render_offline_brand import render, resolved_variant, validate_page
    if not automatic_body(page):
        return False
    content = page['content']
    if not isinstance(content.get('type'), str) or ('free_layout' in content and not plain_items(content)):
        return False
    required = list(text_fields(content))
    for candidate in guided_alternatives(content, repeat=repeat):
        candidate.setdefault('title', page.get('title') or page['purpose'])
        candidate['_deck_page_number'] = choice['page']
        kind = candidate['type']
        trial = {'status': 'guided_trial', 'type': kind, 'variant': candidate.get('variant'),
                 'trigger': 'second_consecutive' if repeat else 'capacity_fallback'}
        trial_path = path.with_name(path.stem + '-guided-trial.pptx')
        try:
            validate_page(candidate, choice['page'])
            variant = resolved_variant(candidate, kind) or None
            if (kind, variant) == previous:
                continue
            render({'theme': theme, 'complete_deck': False, 'pages': [candidate]}, trial_path)
            if not retains_text(trial_path, required):
                raise ValueError('部分原文字段未出现在可编辑对象中')
        except ValueError as exc:
            choice['trial_results'].append(dict(trial, result='rejected', reason=str(exc)))
            continue
        trial_path.replace(path)
        choice['trial_results'].append(dict(trial, result='selected', editable_text_verified=True))
        for key in ('source_mapping', 'atomic_variant', 'body_header', 'family_id', 'classification_status',
                    'canonical_relation', 'matched_role', 'matched_relation', 'fit_signals', 'diversity_gap'):
            choice.pop(key, None)
        choice.update(selection_mode='guided_composition', selection_label='技能排版', source_stamp=None,
                      layout_id=None, fallback_layout_id=kind, variant=variant,
                      reason_code='SECOND_CONSECUTIVE_LAYOUT' if repeat else 'GUIDED_ALTERNATIVE_FIT',
                      selection_reason='试排通过，原文完整保留在可编辑对象中')
        return True
    return False
