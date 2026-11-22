"""Lossless mappings from generic body data to verified template fields."""
from __future__ import annotations

from pathlib import Path
import re

from relation_match import STRUCTURAL_ROLES, supports_input_structure
from structure_content import titled_items
from text_width import visual_width_units
from atomic_body import mapped_texts as atomic_texts

DECLARED_TITLE_BODY_ADAPTER = 'declared_title_body_fields'


def _has_text(value):
    return isinstance(value, str) and bool(value.strip())


BODY_RELATIONS = {
    'image_gallery': 'image-text',
    'metric_evidence': 'metrics',
    'parallel_metrics': 'metrics',
    'single_focus': 'single-focus',
    'text_hierarchy': 'hierarchy',
    'report_table': 'data-table',
}
BODY_INPUT_RELATIONS = {kind: {relation} for kind, relation in BODY_RELATIONS.items()}
BODY_INPUT_RELATIONS['metric_evidence'].add('data')
BODY_INPUT_RELATIONS['parallel_metrics'].add('data')
BODY_INPUT_RELATIONS['parallel_cards'] = {'parallel-points'}
_CONTEXT = {'type', 'title', 'unit_claims', 'source_refs', 'logo', 'theme', 'library_commit'}


def _only_fields(record, allowed):
    return isinstance(record, dict) and record.keys() <= allowed


def _metric_is_sourced(metric, paragraphs, source_refs):
    if (not _only_fields(metric, {'label', 'value', 'period', 'evidence_index'})
            or not _has_text(metric.get('label')) or not _has_text(metric.get('value'))
            or not isinstance(source_refs, list) or not any(_has_text(ref) for ref in source_refs)
            or not any(char.isdecimal() for char in metric['value'])):
        return False
    index = metric.get('evidence_index')
    if type(index) is not int or not 0 <= index < len(paragraphs):
        return False
    support = paragraphs[index]
    # Match a complete label-to-value quote, not two independent hits in a paragraph.
    label = re.escape(metric['label'])
    value = (re.escape(metric['value'])
             + r'(?!\d|[.,]\d|\s*(?:[%％万亿元㎡人次单倍个]|百分点|千克|公斤|吨|公里|[—–~～-]\s*\d))')
    period = metric.get('period')
    if 'period' not in metric:
        return re.search(label + _METRIC_JOINER + value, support) is not None
    if not _has_text(period):
        return False
    period = re.escape(period)
    return any(re.search(pattern, support) is not None for pattern in (
        period + _METRIC_JOINER + label + _METRIC_JOINER + value,
        label + _METRIC_TARGET + period + _METRIC_JOINER + value,
    ))


_METRIC_JOINER = r'\s*(?:[:：=＝]|为|是|达到|达)?\s*'
_METRIC_TARGET = r'(?:\s*目标(?:为)?\s*[+−-]?\d[\d.,]*(?:[%％]|万元|元)?[，,、]\s*)?'
_METRIC_MONTH = r'\d{1,2}(?:月?\s*[至到—–－~～-]\s*\d{1,2})?月(?:\d{1,2}日)?'
_METRIC_QUARTER = r'(?:第?[一二三四1-4]季度|[上下]半年)'
_METRIC_PERIOD = (
    rf'(?:(?:截至\s*)?(?:\d{{4}}年(?:{_METRIC_MONTH}|{_METRIC_QUARTER})?'
    rf'|{_METRIC_MONTH}|{_METRIC_QUARTER}|(?:\d{{4}}\s*)?Q[1-4])'
    r'|当前|现阶段|[本当上]月|[本当上]周|[本当上]季度|[本当上]年度|[本当上今去]年)'
)
_METRIC_DIGITS = r'(?:[+＋−－-]?\s*[¥￥$€£]?)\s*(?:\d{1,3}(?:[,，]\d{3})+|\d+)(?:[.．]\d+)?'
_METRIC_UNIT = (
    r'(?:(?:万亿|千亿|百万|千万|亿|万|千)?(?:元(?:人民币)?|美元|欧元|港元|平方米|平方公里|'
    r'千瓦时|千克|公斤|公里|公顷|毫秒|分钟|小时|㎡|吨|秒|米|天|年|月|周|日|'
    r'人(?:天|次)?|家|台|项|条|次|单|间|份|套|件|宗|个|户|位|辆|本|笔|名|组|座)'
    r'|万亿|亿元|万|亿|千万|百万|百分点|[%％‰]|℃|°[CF]|倍|[kKMGT]?[Bb](?:ps)?|[TGMK]Hz|ms|kg|km|m²|m³)'
    r'(?:\s*[/／]\s*(?:秒|分钟|小时|天|月|年|人|次|单|台|平方米|㎡|m²|m³|s))?'
)
_METRIC_QUANTITY = rf'{_METRIC_DIGITS}(?:\s*(?:余|多)?\s*{_METRIC_UNIT})?'
_METRIC_VALUE = (
    rf'(?:不超过|不低于|不高于|不少于|不大于|不小于|超过|超出|不足|不到|少于|'
    rf'低于|高于|大于|小于|至多|至少|约为|大约|接近|介于|约|近|逾|超|≥|≤|[<>]=?|'
    rf'(?:同比|环比)?(?:下降|降至|下跌|减少|回落|增长|上升|上涨|增至|升至|提升)(?:了)?)?\s*'
    rf'{_METRIC_QUANTITY}(?:\s*[至到—–－−~～-]\s*{_METRIC_QUANTITY})?'
    rf'(?:\s*(?:以上|以下|左右|以内|以外|上下|之间|余|多))?'
)
_METRIC_QUOTE = re.compile(
    r'(?:^|[。；;，、\n]|[.](?!\d)|,(?!\d{3}(?!\d)))\s*(?:[·•●▪‣]\s*)?'
    rf'(?:(?P<period_before>{_METRIC_PERIOD}){_METRIC_JOINER})?'
    r'(?P<label>[^\d:：=＝,，;；、。\r\n()（）!！?？+＋−－%％‰]{1,28}?'
    r'(?:[（(][^（）()\r\n]{1,12}[）)])?)'
    rf'(?:{_METRIC_TARGET}(?P<period_after>{_METRIC_PERIOD}))?'
    rf'{_METRIC_JOINER}(?P<value>{_METRIC_VALUE})'
    r'(?=\s*(?:$|[。；;，,、\n！!？?（）()]|[.](?!\d)))'
)
_METRIC_IDENTIFIER = re.compile(
    r'(?:编码|编号|文号|序号|型号|版本|款号|年号|批号|批次|代码|账号|帐号|电话|工号|'
    r'口令|地址|邮编|日期|章节|第|ID|ISBN|Code)(?:号)?$', re.IGNORECASE
)
_METRIC_LABELS = (
    r'面积|金额|成本|利润|收入|余额|缺口|净值|产值|造价|工期|时长|时间|耗时|延迟|进度|'
    r'规模|时效|速度|水位|温度|电压|浓度|长度|距离|单价|均价|均值|总额|'
    r'合计|总计|共计|累计|上限|下限|占比|得分|指数|倍率|[量数率额值]'
)
_METRIC_LABEL = re.compile(
    rf'^(?:累计|平均|年均|月均|日均)\S.+'
    rf'|(?:{_METRIC_LABELS}|\b(?:rate|ratio|score|time|duration|amount|cost|count|'
    r'area|latency|throughput|revenue|profit|volume))$',
    re.IGNORECASE,
)
_METRIC_CONTEXT_ONLY = re.compile(
    r'^(?:累计|合计|总计|共计|环比|同比|占比|预计|估算|目标|日均|月均|'
    r'当前|当月|本月|全年|年度|实际|截至|合规|正常|预警|异常|落后|超前|'
    r'升|增加|增长|降低|减少|下降|下滑|降|涨)(?:升|增|下降|降|增长|减少|上升|%|达)?$'
)


def infer_metric(paragraphs, page_title):
    """Choose one clearly supported measure and retain its exact source wording."""
    if not isinstance(paragraphs, list) or not all(_has_text(item) for item in paragraphs):
        return None
    title = page_title.casefold() if _has_text(page_title) else ''
    candidates = {}
    for index, paragraph in enumerate(paragraphs):
        for quote in _METRIC_QUOTE.finditer(paragraph):
            label = quote['label'].strip()
            value = quote['value'].strip()
            period = quote['period_before'] or quote['period_after']
            topic = re.split(r'[（(]', label, maxsplit=1)[0].strip()
            if not topic or _METRIC_IDENTIFIER.search(topic) or _METRIC_CONTEXT_ONLY.fullmatch(topic):
                continue
            if (re.search(r'(?:目标|计划|预计|估算|预期|预测|拟定|依次|分别|约为|达到)$', topic)
                    or re.match(r'(?:(?:下月|下周|明年|未来)\s*)?'
                                r'(?:预计|估算|估计|预估|预期|预测|目标|计划|拟实现|拟定)', topic)
                    or re.search(r'(?:计划|拟|将)(?:达成|达到|新增|实现|投入|覆盖)|力争|有望', topic)):
                continue
            metric = {'label': label, 'value': value, 'evidence_index': index}
            if period:
                metric['period'] = period
            # The caller validates actual source references before attaching this quote.
            if not _metric_is_sourced(metric, paragraphs, [paragraph]):
                continue
            topical_start = re.sub(r'^(?:累计|平均|年均|月均|日均)', '', topic.casefold())
            label_start = re.match(r'[a-z][a-z0-9_]+|[\u3400-\u9fff]{2}|[a-z]', topical_start)
            topical = bool(label_start and label_start[0] in title)
            explicit = _METRIC_LABEL.search(topic)
            if not (explicit or topical or quote['period_after']):
                continue
            if not (explicit or re.search(_METRIC_UNIT + r'(?=$|\s|以上|以下|左右|之间)', value)):
                continue
            # Distinguish explicit topic matches first and use rate evidence for a broad title.
            rank = (
                topical,
                bool(explicit or quote['period_after']),
                bool(not topical and (quote['period_after'] or topic.endswith('率'))),
                any(fragment in paragraph.casefold() for fragment in re.findall(r'[a-z][a-z0-9_]+', title)),
            )
            key = label, value, period
            if key not in candidates or candidates[key][0] < rank:
                candidates[key] = rank, metric
    if not candidates:
        return None
    best = max(rank for rank, _ in candidates.values())
    finalists = [metric for rank, metric in candidates.values() if rank == best]
    return finalists[0] if len(finalists) == 1 else None


_PARALLEL_LABEL = r'[\u3400-\u9fffA-Za-z]{2,16}?'
_REPORT_SEPARATOR = r'\s*[，,、]\s*'
_PARALLEL_REPORT = re.compile(
    rf'^(?P<heading>{_PARALLEL_LABEL})(?P<metric>累计{_METRIC_JOINER}{_METRIC_VALUE}'
    rf'{_REPORT_SEPARATOR}(?:本月|当月){_METRIC_JOINER}{_METRIC_VALUE}'
    rf'{_REPORT_SEPARATOR}(?:环比|较上月){_METRIC_JOINER}(?:升|降|持平)?{_METRIC_VALUE})'
    r'(?=$|\s*[。；;，,、！？!?])'
)
_REPORT_START = re.compile(
    r'^(?:(?:[•●▪‣-]|\d+[.、]|[（(]\d+[）)])\s*)?'
    r'[\u3400-\u9fffA-Za-z/／ \t]{1,24}?\s*[:：]?\s*'
    rf'(?:累计|本月|当月){_METRIC_JOINER}{_METRIC_VALUE}'
)
_FORECAST_HEADING = re.compile(r'预计|预测|估算|计划|目标|拟定|预算上限')


def infer_parallel_metrics(items):
    """Find comparable report blocks and keep their evidence paragraphs in order."""
    if not isinstance(items, list) or not items or not all(_has_text(item) for item in items):
        return None
    groups = []
    for index, item in enumerate(items):
        text = item.strip()
        if match := _PARALLEL_REPORT.match(text):
            heading = match['heading']
            if (_FORECAST_HEADING.search(heading)
                    or any(group['heading'] == heading for group in groups)):
                return None
            groups.append({'heading': heading, 'metric': match['metric'], 'indices': [index]})
        elif groups and not _REPORT_START.match(text):
            groups[-1]['indices'].append(index)
        else:
            return None
    return groups if len(groups) >= 2 else None


def _sourced_parallel_metrics(groups, items, refs):
    return (isinstance(refs, list) and any(_has_text(ref) for ref in refs)
            and isinstance(groups, list) and groups == infer_parallel_metrics(items))


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
                or picture.get('kind') != 'image' or not _has_text(picture.get('source_path'))
                or not _only_fields(caption, {'kind', 'x', 'y', 'w', 'h', 'text', 'size_pt',
                                              'color_role', 'font_role', 'bold', 'align'})
                or caption.get('kind') != 'text' or not _has_text(caption.get('text'))):
            return None
        if (not all(type(item.get(key)) in (int, float) for item in (picture, caption)
                    for key in ('x', 'y', 'w', 'h'))
                or picture['x'] != caption['x'] or picture['w'] != caption['w']
                or caption['y'] < picture['y'] + picture['h']):
            return None
        pairs.append({'image_path': picture['source_path'], 'caption': caption['text']})
    return pairs


def _label_list(values, size):
    return isinstance(values, list) and len(values) == size and all(
        _has_text(value) and '\n' not in value and '\r' not in value for value in values)


def _ordered_groups(groups, count):
    if not isinstance(groups, list) or not groups:
        return False
    order = []
    for group in groups:
        if (not _only_fields(group, {'heading', 'indices'}) or not _label_list([group.get('heading')], 1)
                or not isinstance(group.get('indices'), list) or not group['indices']
                or any(type(index) is not int for index in group['indices'])):
            return False
        order.extend(group['indices'])
    return order == list(range(count))


def matching_content(page):
    """Add a source-proven matching interpretation while keeping fallback content intact."""
    original = page.get('content') or {}
    if page.get('role') not in STRUCTURAL_ROLES and isinstance(page.get('material_matching_content'), dict):
        return page['material_matching_content'], 'source_material_contract'
    annotation = page.get('body_match')
    if annotation is None or page.get('role') in STRUCTURAL_ROLES:
        kind = original.get('type') if isinstance(original, dict) else None
        if isinstance(kind, str) and kind in BODY_RELATIONS and 'source_refs' in page:
            return dict(original, source_refs=original.get('source_refs', page['source_refs'])), None
        return original, None
    kind = annotation.get('type') if isinstance(annotation, dict) else None
    label = kind if isinstance(kind, str) and kind in BODY_INPUT_RELATIONS else 'invalid'
    rejected = original, f'body_match_rejected:{label}'
    relation = page.get('matching_relation') or page.get('information_relation')
    if (label == 'invalid' or relation not in BODY_INPUT_RELATIONS[kind]
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
                or not isinstance(items, list) or not all(_has_text(item) for item in items)):
            return rejected
        context['items'] = items
        if kind == 'single_focus':
            index = annotation.get('thesis_index')
            if (not _only_fields(annotation, {'type', 'thesis_index'}) or len(items) != 3
                    or type(index) is not int or not 0 <= index < len(items)):
                return rejected
            context['thesis_index'] = index
        elif kind == 'metric_evidence':
            metric = annotation.get('metric')
            refs = page.get('source_refs', original.get('source_refs'))
            if not _only_fields(annotation, {'type', 'metric'}) or not _metric_is_sourced(metric, items, refs):
                return rejected
            context.update(metric=metric, source_refs=refs)
        elif kind == 'parallel_metrics':
            groups = annotation.get('groups')
            refs = page.get('source_refs', original.get('source_refs'))
            if (not _only_fields(annotation, {'type', 'groups'})
                    or not _sourced_parallel_metrics(groups, items, refs)):
                return rejected
            context.update(groups=groups, source_refs=refs)
        elif kind == 'parallel_cards':
            titles = annotation.get('item_titles')
            if (not _only_fields(annotation, {'type', 'item_titles'})
                    or not _label_list(titles, len(items)) or not (cards := titled_items(items, titles))):
                return rejected
            context.update(type='cards', items=cards)
        elif kind == 'text_hierarchy':
            groups = annotation.get('groups')
            if (not _only_fields(annotation, {'type', 'groups'}) or not _label_list(items, len(items))
                    or not _ordered_groups(groups, len(items))):
                return rejected
            context['groups'] = groups
        else:
            columns, row_labels = annotation.get('columns'), annotation.get('row_labels')
            if (not _only_fields(annotation, {'type', 'columns', 'row_labels'})
                    or not _label_list(columns, 2) or not _label_list(row_labels, len(items))
                    or not _label_list(items, len(items))):
                return rejected
            context.update(columns=columns, row_labels=row_labels)
    return context, f'body_match:{kind}'


def adapt_body_input(contract, content, page_title):
    """Validate the typed payload and map it to its reviewed native PowerPoint slots."""
    kind = contract.get('body_input')
    title = content.get('title') or page_title
    items = content.get('items')
    rejected = dict(content), None
    if (not isinstance(kind, str) or kind not in BODY_RELATIONS or content.get('type') != kind or not _has_text(title)
            or not isinstance(items, list) or len(items) not in contract.get('verified_counts', [])):
        return rejected
    texts = {'page.title': title}
    images = []
    if kind == 'image_gallery':
        slots = contract.get('image_slots', [])
        if len(slots) != len(items) or not _only_fields(content, _CONTEXT | {'items'}):
            return rejected
        for slot, item in zip(slots, items, strict=True):
            if (not _only_fields(item, {'image_path', 'caption'}) or not _has_text(item.get('caption'))
                    or not _has_text(item.get('image_path'))):
                return rejected
            path = Path(item['image_path'])
            if not path.is_absolute() or path.suffix.lower() not in {'.jpg', '.jpeg', '.png'} or not path.is_file():
                return rejected
            images.append({'shape_name': slot['shape_name'], 'path': str(path), 'source': str(path)})
            texts[slot['caption_path']] = item['caption']
    else:
        if not all(_has_text(item) for item in items):
            return rejected
        if kind == 'metric_evidence':
            metric = content.get('metric')
            if (not _only_fields(content, _CONTEXT | {'items', 'metric'})
                    or not _metric_is_sourced(metric, items, content.get('source_refs'))):
                return rejected
            texts.update({f'metric.{key}': metric[key] for key in ('label', 'value', 'period') if key in metric})
            texts['evidence'] = '\n'.join(items)
        elif kind == 'parallel_metrics':
            groups = content.get('groups')
            if (not _only_fields(content, _CONTEXT | {'items', 'groups'})
                    or not _sourced_parallel_metrics(groups, items, content.get('source_refs'))
                    or len(groups) != contract.get('group_count')):
                return rejected
            for slot, group in enumerate(groups):
                prefix = f'groups[{slot}]'
                texts[f'{prefix}.heading'] = group['heading']
                texts[f'{prefix}.metric'] = re.sub(r'([，,、])(?=\s*(?:环比|较上月))', r'\1\n', group['metric'], count=1)
                texts[f'{prefix}.body'] = '\n'.join(items[index] for index in group['indices'])
        elif kind == 'single_focus':
            index = content.get('thesis_index')
            if (not _only_fields(content, _CONTEXT | {'items', 'thesis_index'}) or len(items) != 3
                    or type(index) is not int or not 0 <= index < len(items)):
                return rejected
            texts['thesis'] = items[index]
            for slot, evidence in enumerate(items[:index] + items[index + 1:]):
                texts[f'items[{slot}].body'] = evidence
        elif kind == 'text_hierarchy':
            groups = content.get('groups')
            if (not _only_fields(content, _CONTEXT | {'items', 'groups'})
                    or not _label_list(items, len(items)) or not _ordered_groups(groups, len(items))
                    or [len(group['indices']) for group in groups] != contract.get('group_sizes', [2, 2, 1])):
                return rejected
            for slot, group in enumerate(groups):
                texts[f'groups[{slot}].heading'] = group['heading']
                texts[f'groups[{slot}].body'] = '\n'.join(items[index] for index in group['indices'])
        else:
            columns, labels = content.get('columns'), content.get('row_labels')
            if (not _only_fields(content, _CONTEXT | {'items', 'columns', 'row_labels'})
                    or not _label_list(columns, 2) or not _label_list(labels, len(items))
                    or not _label_list(items, len(items))):
                return rejected
            rows = [columns, *[list(row) for row in zip(labels, items, strict=True)]]
            shape_id = contract.get('table_shape_id')
            width = contract.get('table_column_width_units', [])
            if (contract.get('table_columns') != 2 or contract.get('table_rows') != len(rows)
                    or type(shape_id) is not int or len(width) != 2
                    or any(visual_width_units(value) > max_width for row in rows
                           for value, max_width in zip(row, width, strict=True))):
                return rejected
            return dict(content, texts=texts, tables=[{'shape_id': shape_id, 'rows': rows}]), 'report_table_to_fields'
    result = dict(content, texts=texts)
    if images:
        result.pop('items')  # Native images and captions already cover each input item.
        result['images'] = images
    return result, f'{kind}_to_fields'


def classify_trial_failure(message: str) -> str:
    if any(word in message for word in ('缺少字段', '缺少必需', '须提供', '需要提供')):
        return 'MISSING_REQUIRED_FIELD'
    if any(word in message for word in ('容量', '视觉宽度', '允许行数', '溢出')):
        return 'TEXT_OVER_CAPACITY'
    if any(word in message for word in ('图片区域', '图片槽', '替换内容图片')):
        return 'IMAGE_SLOT_MISMATCH'
    if any(word in message for word in ('数量', '项数', 'item_count')):
        return 'ITEM_COUNT_MISMATCH'
    return 'TRIAL_REJECTED'


def structural_required_paths(contract, item_count):
    return contract.get('required_binding_paths_by_count', {}).get(
        str(item_count), contract.get('required_binding_paths', []))


def normalize_binding_path_aliases(contract, content):
    profiles = contract.get('binding_path_aliases_by_count', {})
    count = content.get('item_count')
    count = contract.get('default_item_count') if count is None else count
    aliases = profiles.get(str(count), {})
    texts = content.get('texts')
    if not aliases or not isinstance(texts, dict) or not aliases.keys() & texts.keys():
        return content
    # Leave conflicting names visible so the normal field checks reject them.
    return dict(content, texts={
        aliases[slot] if slot in aliases and aliases[slot] not in texts else slot: value
        for slot, value in texts.items()
    })


def adapt_structural_fields(entry, content, page_title=None, diagnostics=False):
    """Map explicit generic fields without creating missing facts or relationships."""
    import re
    contract = entry.get('matching_contract') or {}
    def packed(payload, adapter, missing=()):
        return (payload, adapter, list(missing)) if diagnostics else (payload, adapter)

    if entry.get('matching_policy') != 'structural' or entry.get('matching_activation') != 'structure_ready':
        return packed(dict(content), None)
    if content.get('texts'):
        return packed(dict(content), None)
    structure = contract.get('structure_type')
    if content.get('structure_type') != structure and not supports_input_structure(content.get('type'), structure):
        return packed(dict(content), None)
    required_paths = structural_required_paths(contract, content.get('item_count'))
    optional_paths = contract.get('optional_binding_paths', [])
    paths = list(required_paths) + [path for path in optional_paths if path not in required_paths]
    items = content.get('items', [])
    array_pattern = re.compile(r'([a-z_]+)\[(\d+)\]\.(.+)')
    numbered_pattern = re.compile(r'([a-z_]+)_(\d+)\.(.+)')
    scalar_pattern = re.compile(r'([a-z_]+)_(\d+)')
    roots = set()
    for path in paths:
        match = (array_pattern.fullmatch(path) or numbered_pattern.fullmatch(path)
                 or scalar_pattern.fullmatch(path))
        if match:
            roots.add(match[1])
    texts, indices, missing = {}, set(), []

    def nested(source, parts):
        """Resolve declared paths, including nested list slots such as tasks[0].body."""
        for part in parts:
            match = re.fullmatch(r'([a-z_]+)\[(\d+)\]', part)
            if match:
                source = source.get(match[1]) if isinstance(source, dict) else None
                index = int(match[2])
                source = source[index] if isinstance(source, list) and index < len(source) else None
            else:
                source = source.get(part) if isinstance(source, dict) else None
        return source

    def item_value(root, index, field):
        source = content.get(root)
        if source is None:
            source = content.get(root + 's')
        if source is None and root == 'item':
            source = content.get('items')
        if source is None and len(roots) == 1:
            source = items
        if not isinstance(source, list) or index >= len(source):
            return None
        item = source[index]
        if isinstance(item, str) and field == 'title':
            return item
        if not isinstance(item, dict):
            return None
        value = nested(item, field.split('.'))
        if value is None and field in ('heading', 'title'):
            value = item.get('title') or item.get('heading')
        if value is None and field == 'body':
            value = item.get('description') or item.get('text')
        return value
    for path in paths:
        value = None
        if path in ('page.title', 'heading'):
            value = content.get('title') or page_title
        else:
            match = array_pattern.fullmatch(path)
            if match:
                root, index, field = match[1], int(match[2]), match[3]
                indices.add(index)
                value = item_value(root, index, field)
            else:
                match = numbered_pattern.fullmatch(path)
                if match:
                    root, index, field = match[1], int(match[2])-1, match[3]
                    indices.add(index)
                    value = item_value(root, index, field)
                else:
                    match = scalar_pattern.fullmatch(path)
                    if match:
                        root, index = match[1], int(match[2])-1
                        indices.add(index)
                        value = item_value(root, index, 'title')
                    else:
                        value = nested(content, path.split('.'))
                        if value is None:
                            value = content.get(path.replace('.', '_'))
                    if value is None and path in ('center.title', 'center.topic'):
                        value = nested(content, ['center', 'title'])
                    if (value is None and path in ('left.title', 'left.body',
                                                   'right.title', 'right.body')
                            and content.get('type') == 'cards'
                            and isinstance(items, list) and len(items) == 2
                            and isinstance(items[0 if path.startswith('left.') else 1], dict)):
                        index = 0 if path.startswith('left.') else 1
                        indices.add(index)
                        value = nested(items[index], [path.split('.')[1]])
                        if value is None and path.endswith('.title'):
                            value = items[index].get('heading')
                        if value is None and path.endswith('.body'):
                            value = items[index].get('description') or items[index].get('text')
        if not _has_text(value):
            if path in required_paths:
                missing.append(path)
        else:
            texts[path] = value
    if not paths or (indices and isinstance(items, list) and items
                     and indices != set(range(len(items)))):
        return packed(dict(content), None, missing or ['item_count'])
    if missing:
        # Diagnostics may inspect capacity for the facts that did map, even
        # when another required field blocks the final fill.
        partial = dict(content, texts=texts) if diagnostics and texts else dict(content)
        return packed(partial, None, missing)
    # A successful field fill must also carry every supplied item fact. A
    # layout that only exposes titles cannot silently consume body paragraphs.
    mapped_values = set(texts.values())
    unused = []
    def check_item_facts(value, path):
        if isinstance(value, str):
            if value.strip() and value not in mapped_values:
                unused.append(path)
        elif isinstance(value, dict):
            for key, child in value.items():
                if key == 'source_refs' or key.endswith('_source_refs'):
                    continue
                check_item_facts(child, f'{path}.{key}')
        elif isinstance(value, list):
            for index, child in enumerate(value):
                check_item_facts(child, f'{path}[{index}]')
    control_keys = {'type', 'structure_type', 'title', 'theme', 'library_commit',
                    'layout_assessment', 'free_layout', 'source_refs', 'layout_id',
                    'unit_claims'}
    for key, value in content.items():
        if (key not in control_keys and not key.startswith('_')
                and key != 'source_refs' and not key.endswith('_source_refs')):
            check_item_facts(value, key)
    if unused:
        return packed(dict(content), None, ['unmapped_input:' + path for path in unused])
    result = dict(content)
    result.update(type='template_fields', structure_type=structure, texts=texts)
    return packed(result, 'declared_structural_fields')


def structural_mapping_issue(entry, content, page_title=None):
    """Explain why a discovered structure cannot preserve its supplied facts."""
    if entry.get('matching_activation') == 'pilot_verified':
        mapped, adapter = _adapt_for_layout_impl(entry['id'], content, page_title, entry)
        if adapter:
            unused = _unmapped_pilot_fields(entry, content, mapped, adapter)
            if unused:
                return {'reason_code': 'INPUT_FACTS_UNMAPPED', 'paths': unused}
        return None
    _, adapter, gaps = adapt_structural_fields(entry, content, page_title, diagnostics=True)
    if adapter or not gaps:
        return None
    if any(path.startswith('unmapped_input:') for path in gaps):
        return {'reason_code': 'INPUT_FACTS_UNMAPPED', 'paths': gaps}
    return {'reason_code': 'MISSING_REQUIRED_FIELD', 'paths': gaps}


# Input kind, exact item count, target field group, and public adapter name.
_TITLE_BODY_LAYOUTS = {
    'content-blue-106': ('cards', 5, 'items', 'five_card_items_to_p106'),
    'content-blue-112': ('cards', 4, 'items', 'four_card_items_to_p112'),
    'content-blue-142': ('cards', 4, 'items', 'four_cards_with_center_to_p142'),
    'content-blue-256': ('process', 4, 'steps', 'four_process_items_to_p256'),
    'content-blue-258': ('process', 4, 'steps', 'four_process_items_to_p258'),
}


def _adapt_title_body_items(layout_id, content, page_title):
    kind, count, group, adapter_name = _TITLE_BODY_LAYOUTS[layout_id]
    items = content.get('items')
    title = content.get('title') or page_title
    if (content.get('type') != kind or not isinstance(items, list) or len(items) != count
            or not isinstance(title, str) or not title.strip()):
        return dict(content), None

    texts = {'page.title': title}
    if layout_id == 'content-blue-142':
        center = content.get('center')
        if not isinstance(center, dict) or not isinstance(center.get('title'), str) or not center['title'].strip():
            return dict(content), None
        texts['center.title'] = center['title']
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not all(
                isinstance(item.get(key), str) and item[key].strip() for key in ('title', 'body')):
            return dict(content), None
        texts[f'{group}[{index}].heading'] = item['title']
        texts[f'{group}[{index}].body'] = item['body']

    adapted = dict(content, texts=texts, item_count=count)
    if layout_id != 'content-blue-142':
        adapted['generic_visual'] = True
    return adapted, adapter_name


def _adapt_declared_title_body_fields(contract, content, page_title):
    """Fill the title/body targets in declared visual reading order."""
    fields = contract['title_body_fields']
    items = content.get('items')
    title = content.get('title') or page_title
    targets = fields['items']
    if (content.get('type') not in contract.get('content_types', [])
            or not isinstance(items, list) or len(items) != len(targets)
            or len(items) not in contract.get('verified_counts', []) or not _has_text(title)
            or not all(isinstance(item, dict) and all(_has_text(item.get(key))
                       for key in ('title', 'body')) for item in items)):
        return dict(content), None

    page_fields = fields.get('page_fields', {})
    for source in contract.get('required_content_fields', []):
        if source not in page_fields or not _has_text(content.get(source)):
            return dict(content), None
    pairs = [(fields['page_title'], title)]
    for target, item in zip(targets, items, strict=True):
        pairs.extend((target[key], item[key]) for key in ('title', 'body'))
    pairs.extend((target, content[source]) for source, target in page_fields.items()
                 if _has_text(content.get(source)))
    texts = dict(pairs)
    if len(texts) != len(pairs):
        return dict(content), None
    adapted = dict(content, texts=texts, item_count=len(items))
    if fields.get('generic_visual') is True:
        adapted['generic_visual'] = True
    return adapted, fields.get('adapter_name', DECLARED_TITLE_BODY_ADAPTER)


def _adapt_for_layout_impl(layout_id: str, content: dict, page_title: str | None = None, entry=None) -> tuple[dict, str | None]:
    """Return a copied payload; never split, invent, or summarize user facts."""
    if entry is not None:
        mapped, adapter = adapt_structural_fields(entry, content, page_title)
        if adapter:
            return mapped, adapter
        contract = entry.get('matching_contract') or {}
        if (entry.get('matching_activation') == 'pilot_verified' and contract.get('policy') == 'structural'
                and 'title_body_fields' in contract and not content.get('texts')):
            return _adapt_declared_title_body_fields(contract, content, page_title)
    if layout_id in ('content-blue-133', 'content-blue-230') and not content.get('texts'):
        items = content.get('items')
        title = content.get('title') or page_title
        expected = 3 if layout_id.endswith('133') else 5
        kind = 'problem_action_pairs' if expected == 3 else 'phase_goal_activity_output'
        keys = (('problem_title', 'problem_body', 'action_title', 'action_body')
                if expected == 3 else ('title', 'goal', 'activity', 'output'))
        extras = ('axis_top', 'axis_bottom', 'problem_label', 'action_label') if expected == 3 else ()
        if (content.get('type') != kind or not _has_text(title)
                or not isinstance(items, list) or len(items) != expected
                or not all(_has_text(content.get(key)) for key in extras)
                or not all(isinstance(item, dict) and all(_has_text(item.get(key)) for key in keys)
                           for item in items)):
            return dict(content), None
        texts = {'page.title': title}
        if expected == 3:
            texts.update({'axis.top': content['axis_top'], 'axis.bottom': content['axis_bottom'],
                          'column.problem': content['problem_label'],
                          'column.action': content['action_label']})
            for i, item in enumerate(items):
                for key in keys:
                    texts[f'pairs[{i}].{key}'] = item[key]
        else:
            for i, item in enumerate(items):
                texts[f'steps[{i}].heading'] = f'{i+1:02d}\n{item["title"]}'
                texts[f'steps[{i}].goal_label'] = content.get('goal_label', '目标')
                texts[f'steps[{i}].activity_label'] = content.get('activity_label', '活动')
                texts[f'steps[{i}].output_label'] = content.get('output_label', '输出')
                for key in ('goal', 'activity', 'output'):
                    texts[f'steps[{i}].{key}'] = item[key]
        adapted = dict(content)
        adapted['texts'] = texts
        if expected == 5:
            # P230's native process-terminal handler consumes items separately;
            # the complete five-slot binding above already supplies every field.
            adapted.pop('items', None)
            adapted.pop('item_count', None)
        else:
            adapted['item_count'] = expected
        return adapted, f'{kind}_{expected}_to_{layout_id}'
    if layout_id == 'content-tech-021' and not content.get('texts'):
        items = content.get('items')
        title = content.get('title') or page_title
        if (content.get('type') != 'framework' or not _has_text(title)
                or not all(_has_text(content.get(k)) for k in ('summary', 'unit'))
                or not isinstance(items, list) or len(items) != 3
                or not all(isinstance(x, dict) and all(
                    _has_text(x.get(k)) for k in ('title', 'subtitle', 'body')) for x in items)):
            return dict(content), None
        texts = {'heading': title, 'summary': content['summary'],
                 'center.count': '3', 'center.unit': content['unit']}
        for i, item in enumerate(items, 1):
            for key in ('title', 'subtitle', 'body'):
                texts[f'item_{i}.{key}'] = item[key]
        adapted = dict(content)
        adapted['texts'] = texts
        adapted.pop('items', None)
        adapted.pop('item_count', None)
        return adapted, 'framework_3_to_content-tech-021'
    if layout_id in ('content-blue-180', 'content-blue-204', 'content-blue-207',
                     'content-blue-214', 'content-blue-240',
                     'content-tech-028') and not content.get('texts'):
        items = content.get('items')
        title = content.get('title') or page_title
        if not isinstance(title, str) or not title.strip() or not isinstance(items, list):
            return dict(content), None
        if layout_id == 'content-blue-180':
            if (content.get('type') != 'stage_matrix' or content.get('order') != 'left_to_right'
                    or len(items) != 4 or not all(
                        isinstance(item, dict) and _has_text(item.get('title')) and _has_text(item.get('label'))
                        and isinstance(item.get('highlights'), list) and len(item['highlights']) == 2
                        and all(isinstance(h, dict) and _has_text(h.get('title')) and _has_text(h.get('body'))
                                for h in item['highlights']) for item in items)):
                return dict(content), None
            texts = {'page.title': title}
            for i, item in enumerate(items):
                prefix = f'areas[{i}]'
                texts.update({f'{prefix}.heading': item['title'], f'{prefix}.label': item['label']})
                for j, highlight in enumerate(item['highlights']):
                    texts.update({f'{prefix}.items[{j}].heading': highlight['title'],
                                  f'{prefix}.items[{j}].body': highlight['body']})
        elif layout_id == 'content-blue-204':
            months = tuple(f'{i}月' for i in range(1, 7))
            if (content.get('type') != 'monthly_timeline' or content.get('order') != 'chronological'
                    or len(items) != 6 or not all(
                        isinstance(item, dict) and item.get('month') == months[i]
                        and all(_has_text(item.get(k)) for k in ('title', 'body'))
                        for i, item in enumerate(items))):
                return dict(content), None
            texts = {'page.title': title}
            for i, item in enumerate(items):
                texts.update({f'months[{i}].heading': item['title'],
                              f'months[{i}].body': item['body']})
        elif layout_id == 'content-blue-207':
            quarters = ('第一季度', '第二季度', '第三季度', '第四季度')
            if (content.get('type') != 'quarter_cycle' or content.get('order') != 'clockwise'
                    or len(items) != 4 or not _has_text(content.get('center_title'))
                    or not all(isinstance(item, dict) and item.get('quarter') == quarters[i]
                               and all(_has_text(item.get(k)) for k in ('title', 'body'))
                               for i, item in enumerate(items))):
                return dict(content), None
            texts = {'page.title': title, 'center.title': content['center_title']}
            for i, item in enumerate(items):
                texts.update({f'quarters[{i}].label': item['quarter'],
                              f'quarters[{i}].heading': item['title'],
                              f'quarters[{i}].body': item['body']})
        elif layout_id == 'content-blue-214':
            import re
            if (content.get('type') != 'monthly_roadmap' or content.get('order') != 'chronological'
                    or len(items) != 6 or not all(isinstance(item, dict)
                        and all(_has_text(item.get(k)) for k in ('date', 'title', 'body'))
                        for item in items)):
                return dict(content), None
            # Native month slots are seven characters wide; October-December overflow.
            dates = [re.fullmatch(r'(\d{4})年([1-9])月', item['date']) for item in items]
            if any(date is None for date in dates):
                return dict(content), None
            serial = [int(date.group(1)) * 12 + int(date.group(2)) for date in dates]
            if any(b != a + 1 for a, b in zip(serial, serial[1:])):
                return dict(content), None
            texts = {'page.title': title}
            for i, item in enumerate(items):
                texts.update({f'months[{i}].date': item['date'],
                              f'months[{i}].heading': item['title'],
                              f'months[{i}].body': item['body']})
        elif layout_id == 'content-blue-240':
            if (content.get('type') != 'serpentine_process' or content.get('order') != 'serpentine'
                    or len(items) != 6 or not _has_text(content.get('center_title'))
                    or not all(isinstance(item, dict)
                               and all(_has_text(item.get(k)) for k in ('title', 'goal', 'body'))
                               for item in items)):
                return dict(content), None
            texts = {'page.title': title, 'center.title': content['center_title']}
            for i, item in enumerate(items):
                texts.update({f'steps[{i}].heading': item['title'],
                              f'steps[{i}].goal': item['goal'],
                              f'steps[{i}].body': item['body']})
        else:
            if (content.get('type') != 'two_phase_plan' or content.get('order') != 'left_to_right'
                    or len(items) != 2 or not _has_text(content.get('summary'))
                    or not all(isinstance(item, dict) and _has_text(item.get('title'))
                               and isinstance(item.get('issues'), list) and len(item['issues']) == 5
                               and all(_has_text(issue) for issue in item['issues']) for item in items)):
                return dict(content), None
            texts = {'heading': title, 'summary': content['summary']}
            for side, item in zip(('left', 'right'), items):
                texts[f'phase_{1 if side == "left" else 2}.title'] = item['title']
                for j, issue in enumerate(item['issues'], 1):
                    texts[f'{side}.issue_{j}'] = issue
        adapted = dict(content)
        adapted['texts'] = texts
        adapted.pop('items', None)
        adapted.pop('item_count', None)
        return adapted, f'{content["type"]}_{len(items)}_to_{layout_id}'
    if layout_id in ('content-blue-261', 'content-blue-266', 'content-tech-018',
                     'schedule-tech-069', 'content-tech-016') and not content.get('texts'):
        items = content.get('items')
        title = content.get('title') or page_title
        if not _has_text(title) or not isinstance(items, list):
            return dict(content), None
        if layout_id == 'content-blue-261':
            if (content.get('type') != 'cycle' or content.get('order') != 'clockwise'
                    or len(items) != 6 or not _has_text(content.get('center_title'))
                    or not all(isinstance(x, dict) and all(_has_text(x.get(k)) for k in ('title', 'body')) for x in items)):
                return dict(content), None
            center = content['center_title']
            if ('\n' not in center and 3 <= len(center) <= 4
                    and all('\u3400' <= char <= '\u9fff' for char in center)):
                center = center[:2] + '\n' + center[2:]
            texts = {'page.title': title, 'center.title': center}
            for i, item in enumerate(items):
                texts.update({f'steps[{i}].heading': item['title'], f'steps[{i}].body': item['body']})
        elif layout_id == 'content-blue-266':
            if (content.get('type') != 'process' or content.get('order') != 'serpentine'
                    or len(items) != 6 or not all(isinstance(x, dict)
                    and all(_has_text(x.get(k)) for k in ('title', 'body')) for x in items)):
                return dict(content), None
            texts = {'page.title': title}
            for i, item in enumerate(items):
                texts.update({f'steps[{i}].heading': item['title'], f'steps[{i}].body': item['body']})
        elif layout_id == 'content-tech-018':
            if (content.get('type') != 'hierarchy' or content.get('order') != 'bottom_to_top'
                    or len(items) != 3 or not all(isinstance(x, dict) and _has_text(x.get('body')) for x in items)
                    or not all(_has_text(content.get(k)) for k in ('summary', 'left_support', 'right_support'))):
                return dict(content), None
            texts = {'heading': title, 'summary': content['summary'],
                     'left_support': content['left_support'], 'right_support': content['right_support']}
            for i, item in enumerate(items):
                texts[f'tier_{3-i}.body'] = item['body']
        elif layout_id == 'schedule-tech-069':
            import re
            labels = content.get('column_labels')
            if (content.get('type') != 'schedule' or content.get('order') != 'chronological'
                    or len(items) != 6 or not _has_text(content.get('summary'))
                    or not isinstance(labels, dict)
                    or not all(_has_text(labels.get(k)) for k in ('time', 'activity', 'owner'))
                    or not all(isinstance(x, dict)
                    and all(_has_text(x.get(k)) for k in ('time', 'activity', 'owner')) for x in items)):
                return dict(content), None
            ranges = [re.fullmatch(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', x['time'].strip()) for x in items]
            if any(x is None for x in ranges):
                return dict(content), None
            minutes = [(int(x[1])*60+int(x[2]), int(x[3])*60+int(x[4])) for x in ranges]
            if any(start >= end or end > 24*60 for start, end in minutes) or any(
                    minutes[i][1] > minutes[i+1][0] for i in range(5)):
                return dict(content), None
            texts = {'heading': title, 'summary': content['summary'],
                     'table.time_heading': labels['time'],
                     'table.activity_heading': labels['activity'],
                     'table.owner_heading': labels['owner']}
            for i, item in enumerate(items, 1):
                for key in ('time', 'activity', 'owner'):
                    texts[f'row_{i}.{key}'] = item[key]
        else:
            if (content.get('type') != 'framework' or len(items) != 5
                    or not all(_has_text(content.get(k)) for k in ('summary', 'unit'))
                    or not all(isinstance(x, dict)
                    and all(_has_text(x.get(k)) for k in ('title', 'body')) for x in items)):
                return dict(content), None
            texts = {'heading': title, 'summary': content['summary'],
                     'center.count': '5', 'center.unit': content['unit']}
            for i, item in enumerate(items, 1):
                texts[f'item_{i}.label'] = item['title']
                texts[f'item_{i}.body'] = item['body']
        adapted = dict(content)
        adapted['texts'] = texts
        adapted.pop('items', None)
        adapted.pop('item_count', None)
        return adapted, f'{content["type"]}_{len(items)}_to_{layout_id}'
    # These layouts were visually reviewed for cross-scenario reuse. Every
    # explanatory field below comes from the request; only ordinal markers are
    # computed. A missing conclusion, outcome, or tag rejects the adapter.
    new_contracts = {
        'content-blue-060': ('process', 4, ('title', 'body', 'outcome'), ('goal',)),
        'content-blue-267': ('process', 4, ('title', 'body'), ()),
        'content-tech-026': ('comparison', 4, ('title', 'body'), ('summary',)),
        'content-tech-029': ('comparison', 2, ('title', 'body'), ('summary', 'conclusion')),
        'content-tech-040': ('comparison', 2, ('title', 'body', 'tags'), ('summary',)),
        'content-tech-048': ('cards', 4, ('title', 'body'), ('conclusion',)),
        'content-tech-033': ('cards', 5, ('title', 'body'), ('summary', 'conclusion')),
        'content-tech-054': ('process', 4, ('title', 'body'), ('summary',)),
        'content-tech-063': ('milestone_timeline', 5, ('label', 'body'), ('summary',)),
        'content-tech-064': ('milestone_timeline', 5, ('label', 'title'), ('summary',)),
        'content-tech-065': ('milestone_timeline', 5, ('label', 'body'), ('summary',)),
        'content-tech-034': ('cards', 5, ('title', 'body'), ('summary',)),
        'content-tech-037': ('cards', 3, ('title', 'body'), ('summary',)),
        'content-tech-038': ('process', 4, ('title', 'body'), ('summary',)),
        'content-tech-043': ('cards', 3, ('title', 'body'), ('summary',)),
        'content-tech-020': ('cards', 6, ('title',), ('summary', 'center.topic')),
        'content-tech-042': ('cycle', 4, ('title', 'body'), ('conclusion',)),
        'content-tech-045': ('process', 4, ('title', 'body'), ()),
        'content-tech-081': ('hierarchy', 3, ('title', 'body'), ()),
    }
    if layout_id in new_contracts and not content.get('texts'):
        kind, count, required, extras = new_contracts[layout_id]
        items = content.get('items')
        title = content.get('title') or page_title
        def extra_value(path):
            value = content
            for part in path.split('.'):
                value = value.get(part) if isinstance(value, dict) else None
            return value
        valid = (content.get('type') == kind and isinstance(items, list) and len(items) == count
                 and isinstance(title, str) and title.strip()
                 and (layout_id != 'content-tech-081' or content.get('order') == 'top_to_bottom')
                 and all(isinstance(extra_value(key), str) and extra_value(key).strip() for key in extras)
                 and all(isinstance(item, dict) and all(
                     isinstance(item.get(key), str) and item[key].strip()
                     if key != 'tags' else isinstance(item.get('tags'), list) and len(item['tags']) == 2
                     and all(isinstance(tag, str) and tag.strip() for tag in item['tags'])
                     for key in required) for item in items))
        if not valid:
            return dict(content), None
        texts = {'page.title' if layout_id.startswith('content-blue-') else 'heading': title}
        if layout_id == 'content-blue-060':
            texts['page.goal'] = content['goal']
            for i, item in enumerate(items):
                prefix = f'steps[{i}]'
                texts.update({f'{prefix}.number': f'{i+1:02d}', f'{prefix}.title': item['title'],
                              f'{prefix}.body': item['body'], f'{prefix}.outcome': item['outcome']})
        elif layout_id == 'content-blue-267':
            for i, item in enumerate(items):
                texts.update({f'steps[{i}].heading': item['title'], f'steps[{i}].body': item['body']})
        elif layout_id == 'content-tech-026':
            texts['summary'] = content['summary']
            for i, item in enumerate(items, 1):
                texts.update({f'issue_{i}.number': f'{i:02d}', f'issue_{i}.title': item['title'],
                              f'issue_{i}.body': item['body']})
        elif layout_id in ('content-tech-029', 'content-tech-040'):
            texts['summary'] = content['summary']
            for key, item in zip(('left', 'right'), items):
                texts.update({f'{key}.title': item['title'], f'{key}.body': item['body']})
                if layout_id == 'content-tech-040':
                    texts.update({f'{key}.tag_1': item['tags'][0], f'{key}.tag_2': item['tags'][1]})
            if layout_id == 'content-tech-029':
                texts['bottom.conclusion'] = content['conclusion']
        elif layout_id == 'content-tech-033':
            # The source labels are swapped: bottom_conclusion renders as the
            # page heading, and heading renders as the bottom takeaway.
            texts.update({'heading': content['conclusion'], 'bottom_conclusion': title,
                          'summary': content['summary']})
            for i, item in enumerate(items, 1):
                texts.update({f'item_{i}.title': item['title'], f'item_{i}.body': item['body']})
        elif layout_id == 'content-tech-054':
            texts['summary'] = content['summary']
            for i, item in enumerate(items, 1):
                texts.update({f'item_{i}.title': item['title'], f'item_{i}.body': item['body'],
                              f'item_{i}.number': f'{i:02d}'})
        elif layout_id in ('content-tech-063', 'content-tech-064', 'content-tech-065'):
            texts['summary'] = content['summary']
            for i, item in enumerate(items, 1):
                if layout_id == 'content-tech-064':
                    texts.update({f'item_{i}.year': item['label'], f'item_{i}.event': item['title']})
                else:
                    prefix = f'milestone_{i}'
                    texts.update({f'{prefix}.body': item['body'],
                                  f'{prefix}.year' if layout_id.endswith('063') else f'{prefix}.date': item['label']})
        elif layout_id in ('content-tech-034', 'content-tech-037',
                           'content-tech-038', 'content-tech-043'):
            texts['summary'] = content['summary']
            for i, item in enumerate(items, 1):
                texts.update({f'item_{i}.title': item['title'], f'item_{i}.body': item['body']})
                if layout_id == 'content-tech-038':
                    texts[f'item_{i}.number'] = f'{i:02d}'
        elif layout_id == 'content-tech-020':
            texts.update({'summary': content['summary'], 'center.topic': content['center']['topic']})
            for i, item in enumerate(items):
                side = 'left' if i < 3 else 'right'
                texts[f'{side}_{i % 3 + 1}.title'] = item['title']
        elif layout_id in ('content-tech-042', 'content-tech-045',
                           'content-tech-081'):
            if layout_id == 'content-tech-042':
                texts['center.conclusion'] = content['conclusion']
            if layout_id == 'content-tech-045':
                texts['summary'] = content.get('summary') or title
            for i, item in enumerate(items, 1):
                if layout_id == 'content-tech-081':
                    texts.update({f'stage_{i}.title': item['title'], f'stage_{i}.body': item['body']})
                else:
                    texts.update({f'item_{i}.title': item['title'], f'item_{i}.body': item['body']})
                    if layout_id == 'content-tech-045':
                        texts[f'item_{i}.step'] = f'{i:02d}'
        else:  # P048's title and body binding indices have different source order.
            if isinstance(content.get('summary'), str) and content['summary'].strip():
                texts['summary'] = content['summary']
            texts['top_conclusion'] = content['conclusion']
            for i, (title_index, body_index) in enumerate(zip((3, 4, 2, 1), (2, 1, 3, 4))):
                item = items[i]
                texts.update({f'item_{title_index}.title': item['title'],
                              f'item_{body_index}.body': item['body']})
        adapted = dict(content)
        adapted['texts'] = texts
        if layout_id in ('content-tech-038', 'content-tech-042', 'content-tech-045',
                         'content-tech-081'):
            # The source's variable-column path is an unverified internal
            # prototype. Reuse only its fixed four reviewed text slots.
            adapted.pop('items', None)
            adapted.pop('item_count', None)
            return adapted, f'{kind}_{count}_to_{layout_id}'
        # P026 has four reviewed issue slots but its old cardinality rule has
        # no source_count; an explicit item_count would be read as reflow.
        if layout_id != 'content-tech-026':
            adapted['item_count'] = count
        return adapted, f'{kind}_{count}_to_{layout_id}'
    if layout_id in ('content-blue-181', 'content-blue-199') and not content.get('texts'):
        items = content.get('items')
        title = content.get('title') or page_title
        is_layers = layout_id.endswith('181')
        expected_type = 'hierarchy' if is_layers else 'milestone_timeline'
        required = ('title', 'body') if is_layers else ('label', 'title', 'body')
        if (content.get('type') == expected_type and isinstance(items, list)
                and len(items) == (4 if is_layers else 5)
                and isinstance(title, str) and title.strip()
                and (not is_layers or content.get('order') == 'inner_to_outer')
                and all(isinstance(item, dict) and all(isinstance(item.get(key), str)
                        and item[key].strip() for key in required) for item in items)):
            texts = {'page.title': title}
            for index, item in enumerate(items):
                prefix = f'layers[{index}]' if is_layers else f'years[{index}]'
                texts[f'{prefix}.heading'] = item['title']
                texts[f'{prefix}.body'] = item['body']
                if not is_layers:
                    texts[f'{prefix}.label'] = item['label']
            adapted = dict(content)
            adapted['texts'] = texts
            adapted['item_count'] = len(items)
            return adapted, ('four_nested_layers_to_p181' if is_layers
                             else 'five_year_milestones_to_p199')
    if layout_id == 'content-blue-076' and not content.get('texts'):
        directions = content.get('items')
        center = content.get('center')
        title = content.get('title') or page_title
        if (content.get('type') == 'directions' and isinstance(directions, list)
                and len(directions) == 4 and isinstance(center, dict)
                and isinstance(center.get('title'), str) and center['title'].strip()
                and isinstance(title, str) and title.strip()
                and all(isinstance(item, dict) and all(isinstance(item.get(key), str)
                        and item[key].strip() for key in ('heading', 'body', 'short'))
                        for item in directions)):
            texts = {'page.title': title, 'center.title': center['title']}
            for index, item in enumerate(directions):
                for key in ('heading', 'body', 'short'):
                    texts[f'directions[{index}].{key}'] = item[key]
            adapted = dict(content)
            adapted['texts'] = texts
            adapted['item_count'] = 4
            return adapted, 'four_directions_with_center_to_p076'
    if layout_id in _TITLE_BODY_LAYOUTS and not content.get('texts'):
        return _adapt_title_body_items(layout_id, content, page_title)
    return dict(content), None


def unmapped_pilot_input_paths(content: dict, mapped: dict) -> list[str]:
    """Find user text omitted by an older pilot adapter's output slots."""
    texts = mapped.get('texts') if isinstance(mapped.get('texts'), dict) else {}
    rendered = [''.join(value.split()) for value in texts.values() if isinstance(value, str)]
    unused = []
    control = {'type', 'structure_type', 'title', 'order', 'theme', 'library_commit',
               'item_count', 'layout_id', 'source_refs', 'unit_claims',
               'layout_assessment', 'free_layout'}
    # These are checked against fixed axis/position rules rather than copied
    # into editable fields. The original template renders the category labels.
    positional = {'month', 'quarter'}
    def walk(value, path, key=''):
        if isinstance(value, str):
            normalized = ''.join(value.split())
            if normalized and key not in positional and not any(normalized in text for text in rendered):
                unused.append('unmapped_input:' + path)
        elif isinstance(value, dict):
            for child_key, child in value.items():
                if child_key == 'source_refs' or child_key.endswith('_source_refs'):
                    continue
                if not path and (child_key in control or child_key.startswith('_')):
                    continue
                walk(child, f'{path}.{child_key}' if path else child_key, child_key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f'{path}[{index}]', key)
    walk(content, '')
    return unused


def _unmapped_pilot_fields(entry, content, mapped, adapter):
    fields = (entry.get('matching_contract') or {}).get('title_body_fields')
    if fields is None or adapter != fields.get('adapter_name', DECLARED_TITLE_BODY_ADAPTER):
        return unmapped_pilot_input_paths(content, mapped)
    return unmapped_title_body_fields(content, fields.get('page_fields', {}))


def unmapped_title_body_fields(content, page_fields=()):
    """List supplied facts outside the card and supported page fields."""
    control = {'type', 'structure_type', 'title', 'theme', 'library_commit', 'item_count',
               'layout_id', 'unit_claims', 'layout_assessment', 'free_layout', 'logo', 'variant'}

    def unused_fields(record, allowed, prefix=''):
        paths = []
        for key, value in record.items():
            if (key in allowed or key == 'source_refs' or key.endswith('_source_refs')
                    or (not prefix and key.startswith('_'))):
                continue
            present = value.strip() if isinstance(value, str) else value not in (None, [], {})
            if present:
                paths.append(f'unmapped_input:{prefix}{key}')
        return paths

    mapped_page_fields = {key for key in page_fields if _has_text(content.get(key))}
    unused = unused_fields(content, control | {'items'} | mapped_page_fields)
    items = content.get('items')
    if isinstance(items, list):
        for index, item in enumerate(items):
            if isinstance(item, dict):
                unused.extend(unused_fields(item, {'title', 'body'}, f'items[{index}].'))
    return unused


def adapt_for_layout(layout_id: str, content: dict, page_title: str | None = None, entry=None) -> tuple[dict, str | None]:
    atomic = (entry or {}).get('atomic_variant')
    if atomic:
        texts = atomic_texts(atomic, content, page_title)
        if texts is None:
            return dict(content), None
        return dict(content, type='template_fields', texts=texts, item_count=atomic['count']), 'atomic_items_to_fields'
    contract = (entry or {}).get('matching_contract') or {}
    if contract.get('body_input'):
        return adapt_body_input(contract, content, page_title)
    normalized = normalize_binding_path_aliases(contract, content)
    mapped, adapter = _adapt_for_layout_impl(layout_id, normalized, page_title, entry)
    if (adapter and entry and entry.get('matching_activation') == 'pilot_verified'
            and content.get('type') != 'template_fields'
            and _unmapped_pilot_fields(entry, content, mapped, adapter)):
        return dict(content), None
    return mapped, adapter or ('registered_binding_path_aliases' if normalized is not content else None)


def field_source_evidence(content: dict, mapped: dict) -> dict:
    """Record auditable input-field candidates without claiming unique origins."""
    leaves = []
    control = {'type', 'structure_type', 'order', 'theme', 'library_commit',
               'item_count', 'layout_id', 'source_refs', 'unit_claims',
               'layout_assessment', 'free_layout'}
    def walk(value, path=''):
        if isinstance(value, str):
            if value.strip():
                leaves.append((path, ''.join(value.split())))
        elif isinstance(value, dict):
            for key, child in value.items():
                if key == 'source_refs' or key.endswith('_source_refs'):
                    continue
                if not path and (key in control or key.startswith('_')):
                    continue
                walk(child, f'{path}.{key}' if path else key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f'{path}[{index}]')
    walk(content)
    source_refs = content.get('source_refs') if isinstance(content.get('source_refs'), list) else []
    texts = mapped.get('texts') if isinstance(mapped.get('texts'), dict) else {}
    evidence = {}
    for target, value in texts.items():
        normalized = ''.join(value.split()) if isinstance(value, str) else ''
        candidates = [path for path, source_value in leaves
                      if source_value and source_value in normalized]
        evidence[target] = {'input_paths': candidates, 'source_refs': source_refs,
                            'status': ('matched_input_text' if candidates else
                                       'generated_label_or_reformatted')}
    return evidence
