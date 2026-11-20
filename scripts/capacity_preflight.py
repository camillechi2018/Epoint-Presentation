"""Read binding and reviewed long-copy limits before trying a source layout."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from library_location import binding_path_key
from content_adapters import adapt_for_layout
from text_width import binding_text_issues, visual_width_units
from body_header import checked_title, contract_for


@lru_cache(maxsize=8)
def _review(root: str):
    library = Path(root)
    capacity_path = library / 'review' / 'body-longcopy-capacity.json'
    policy_path = library / 'review' / 'body-capacity-preflight-policy.json'
    if not capacity_path.is_file():
        return {}, {}, None, None
    capacity = json.loads(capacity_path.read_text(encoding='utf-8-sig'))
    policy = (json.loads(policy_path.read_text(encoding='utf-8-sig'))
              if policy_path.is_file() else {'near_hard_limit_ratio': .85,
                                             'near_recommended_limit_ratio': .9})
    by_layout = {item['layout_id']: {field['semantic_path']: field
                                    for field in item.get('fields', [])}
                 for item in capacity.get('layouts', [])}
    return (by_layout, policy, hashlib.sha256(capacity_path.read_bytes()).hexdigest(),
            hashlib.sha256(policy_path.read_bytes()).hexdigest() if policy_path.is_file() else None)


@lru_cache(maxsize=2048)
def _bindings(path: str):
    file = Path(path)
    return json.loads(file.read_text(encoding='utf-8-sig'))['fields'], hashlib.sha256(file.read_bytes()).hexdigest()


def required_input_fields(fields):
    reserved = {'brand_locked', 'decoration_locked', 'source_decorative_locked', 'computed_item_count'}
    return [field for field in fields if field.get('required', True) is not False
            and field.get('semantic_role') not in reserved and field['field'] != 'brand']


def missing_binding_paths(fields, content):
    texts = content.get('texts')
    provided = set(texts) if isinstance(texts, dict) else set()
    return [field.get('semantic_path') or field['field'] for field in required_input_fields(fields)
            if field['field'] not in provided and field.get('semantic_path') not in provided]


def _safe_wrap(value: str, width: int, max_lines: int, max_chars: int,
               prefer_three: bool = False) -> str | None:
    if '\n' in value or max_lines < 2 or len(value) + 1 > max_chars:
        return None

    def penalty(at: int) -> int:
        if value[at - 1] in '，；。！？、：）,:;.!?)':
            return 0
        return 25

    line_counts = [2]
    if (prefer_three and max_lines >= 3 and len(value) + 2 <= max_chars
            and visual_width_units(value) >= width * 1.15):
        line_counts = [3, 2]
    for count in line_counts:
        choices = []
        if count == 2:
            cuts = ((at,) for at in range(1, len(value)))
        else:
            cuts = ((first, second) for first in range(1, len(value) - 1)
                    for second in range(first + 1, len(value)))
        for positions in cuts:
            if any((value[at - 1].isascii() and value[at].isascii())
                   or (value[at - 1].isdigit() and not value[at].isascii())
                   for at in positions):
                continue
            edges = (0, *positions, len(value))
            lines = [value[edges[i]:edges[i + 1]] for i in range(count)]
            widths = [visual_width_units(line) for line in lines]
            if max(widths) > width:
                continue
            score = max(widths) - min(widths) + sum(penalty(at) for at in positions)
            choices.append((score, positions, '\n'.join(lines)))
        if choices:
            return min(choices)[2]
    return None


def preflight(library: Path, entry: dict, content: dict, page_title: str | None,
              theme: str, *, body_header_pilot=False) -> dict:
    """Return hard binding failures, advisory long-copy pressure and wrap options."""
    library = Path(library).resolve()
    mapped, adapter = adapt_for_layout(entry['id'], content, page_title, entry=entry)
    texts = mapped.get('texts') if isinstance(mapped.get('texts'), dict) else {}
    contract = contract_for(entry, theme, body_header_pilot and content.get('logo') is None)
    binding_rel = contract['bindings'] if contract else entry[binding_path_key(entry, theme)]
    bindings, binding_sha = _bindings(str(library / binding_rel))
    longcopy, policy, longcopy_sha, policy_sha = _review(str(library))
    reviewed_fields = longcopy.get(entry['id'], {})
    hard, advisory, wrap_suggestions, details = [], [], {}, []
    header = {}
    if contract:
        try:
            title_field = contract['title_input']
            if binding_sha != contract['bindings_sha256']:
                raise ValueError('BODY_HEADER_BINDING_HASH_MISMATCH')
            header['body_header_title'] = checked_title(title_field, texts, page_title, contract)
            header['body_header_binding_path'] = title_field['semantic_path']
        except (ValueError, KeyError, TypeError) as exc:
            hard.append({'field': 'page.title', 'rule': str(exc)})
    margins = []
    near_hard = policy.get('near_hard_limit_ratio', .85)
    near_reviewed = policy.get('near_recommended_limit_ratio', .9)
    for field in bindings:
        semantic = field.get('semantic_path')
        key = semantic if semantic in texts else field['field'] if field['field'] in texts else None
        if key is None:
            continue
        value = texts[key]
        if not isinstance(value, str) or (field.get('required') is False and not value.strip()):
            continue
        char_limit = field.get('max_chars')
        line_limit = field.get('max_lines')
        width_limit = field.get('max_width_units')
        lines = value.split('\n')
        widest = max(visual_width_units(line) for line in lines)
        reasons = binding_text_issues(value, field, width_units=widest)
        if reasons == ['max_width_units']:
            suggestion = _safe_wrap(value, int(width_limit), line_limit or 1,
                                    char_limit or 9999,
                                    prefer_three=field.get('semantic_role') == 'body')
            if suggestion and not binding_text_issues(suggestion, field):
                reasons.clear()
                wrap_suggestions[key] = suggestion
                if field.get('semantic_role') == 'body':
                    source_lines = suggestion.split('\n')
                    if any(line and line[-1] not in '，；。！？、：）,:;.!?)'
                           for line in source_lines[:-1]):
                        advisory.append({'field': semantic or field['field'],
                                         'rule': 'mid_phrase_wrap_review'})
        # The pilot's reviewed wrap width improves line breaks without lowering
        # the existing binding limits or changing any supplied words.
        wrap_width = contract.get('preferred_body_wrap_width_units') if contract else None
        if (not reasons and key not in wrap_suggestions and field.get('semantic_role') == 'body'
                and isinstance(wrap_width, int) and wrap_width > 0
                and len(lines) == 1 and widest > wrap_width):
            suggestion = _safe_wrap(value, wrap_width, min(line_limit or 1, 2), char_limit or 9999)
            if suggestion and not binding_text_issues(suggestion, field):
                wrap_suggestions[key] = suggestion
                advisory.append({'field': semantic or field['field'], 'rule': 'body_header_pilot_wrap'})
        for reason in reasons:
            hard.append({'field': semantic or field['field'], 'rule': reason,
                         'actual_chars': len(value), 'binding_field': field['field']})
        field_margins = []
        if isinstance(char_limit, int) and char_limit > 0:
            field_margins.append((char_limit-len(value))/char_limit)
            if len(value) >= char_limit*near_hard:
                advisory.append({'field': semantic or field['field'], 'rule': 'near_binding_chars'})
        if isinstance(width_limit, (int, float)) and width_limit > 0:
            field_margins.append((width_limit-widest)/width_limit)
            if widest >= width_limit*near_hard and key not in wrap_suggestions:
                advisory.append({'field': semantic or field['field'], 'rule': 'near_binding_width'})
        if field_margins:
            margins.append(min(field_margins))
        reviewed = reviewed_fields.get(semantic, {})
        recommended = reviewed.get('recommended_max_cjk_chars')
        if (isinstance(recommended, int) and recommended > 0 and '\n' not in value):
            cjk_equivalent = visual_width_units(value) / 2
            if cjk_equivalent >= recommended*near_reviewed:
                advisory.append({'field': semantic, 'rule': 'near_reviewed_longcopy',
                                 'recommended_cjk_chars': recommended,
                                 'actual_cjk_equivalent': round(cjk_equivalent, 1)})
        details.append({'field': semantic or field['field'], 'role': field.get('semantic_role'),
                        'actual_chars': len(value), 'max_chars': char_limit,
                        'actual_lines': len(lines), 'max_lines': line_limit,
                        'max_visual_width_units': widest,
                        'binding_max_width_units': width_limit,
                        'reviewed_recommended_cjk_chars': recommended})
    rules_rel = entry.get('layout_rules')
    rules_file = library / rules_rel if rules_rel else None
    rules = json.loads(rules_file.read_text(encoding='utf-8-sig')) if rules_file and rules_file.is_file() else {}
    rules_sha = hashlib.sha256(rules_file.read_bytes()).hexdigest() if rules_file and rules_file.is_file() else None
    title_pressure = rules.get('title_pressure_test') or {}
    safe_title_chars = title_pressure.get('safe_title_chars')
    if not contract and isinstance(safe_title_chars, int) and page_title and len(page_title) > safe_title_chars:
        advisory.append({'field': 'page.title', 'rule': 'layout_title_pressure',
                         'actual_chars': len(page_title), 'safe_title_chars': safe_title_chars})
    return {'status': ('hard_overflow' if hard else 'wrap_possible' if wrap_suggestions else
                       'ready' if texts else 'awaiting_mapping'),
            'content_adapter': adapter, 'hard_issues': hard, 'advisory': advisory,
            'wrap_suggestions': wrap_suggestions, 'capacity_margin': min(margins) if margins else None,
            'fields': details, 'binding_path': binding_rel, 'binding_sha256': binding_sha,
            'longcopy_sha256': longcopy_sha, 'policy_sha256': policy_sha,
            'layout_rules_sha256': rules_sha,
            'layout_title_pressure_safe_chars': safe_title_chars if not contract else None,
            **header}
