"""Discover same-theme body contracts against source paragraphs before drafting slides."""
import json
import re
from functools import lru_cache

from library_location import text_binding_path

from content_adapters import structural_required_paths
from plan_deck import count_profile


def comparison_facts(raw):
    pairs = []
    for line in raw.splitlines():
        match = re.search(r'(?:^|[；;])(?:在|就|针对)(.{1,10}?)(?:上|方面)[，,](.*)', line)
        if not match:
            continue
        halves = re.split(r'(?:”|」)[，,\s]*(?:到|变为|调整为|转变为|转向|转为)(?=[“「])', match[2], maxsplit=1)
        if len(halves) != 2:
            return []
        left = re.findall(r'[“「]([^”」]+)[”」]', halves[0] + '”')
        right = re.findall(r'[“「]([^”」]+)[”」]', halves[1])
        if len(left) != 2 or len(right) != 2:
            return []
        pairs.append((match[1], left, right))
    return pairs if len(pairs) >= 2 else []


def coordination_facts(raw):
    """Read ordered action clauses, their actual objects, and a stated start/end."""
    if re.search(r'尚未|不得|未能|不应|取消预约', raw):
        return None
    clauses = re.findall(r'([^，。；\n]+)([，。；\n]*)', raw.strip())
    if len(clauses) < 4:
        return None
    initial = re.fullmatch(r'(?:依据|根据|参照|按照)(.+)', clauses[0][0])
    end = clauses[-1][0]
    if not initial or not re.match(r'(?:做好|完成|达到|确保|取得|形成|以便)', end):
        return None

    def entities(phrase):
        return [s for s in re.split(r'、|以及|和|及', phrase) if s]

    steps = []
    subject = ''
    for pos, (clause, punctuation) in enumerate(clauses[1:]):
        plain = re.sub(r'^(?:首先|随后|提前|同时|最后|然后|再|先)', '', clause)
        create = re.fullmatch(r'(建立|制定|编制|编写|生成)(.+)', plain)
        notify = re.fullmatch(r'向(.+?)(报备|备案|报告|通知|发送|汇报)', plain)
        reserve = re.fullmatch(r'(预约|预订|安排|联系|调度)(.+)', plain)
        check = re.fullmatch(r'(?:逐项|逐一)?(?:核对|检查|确认|登记)(.+)', plain)
        last = pos == len(clauses)-2
        if last or check or not (create or notify or reserve):
            if not steps:
                return None
            steps[-1]['method'] += clause + punctuation
            if check and not steps[-1]['tags']:
                steps[-1]['tags'] = entities(check[1])
            continue
        if create:
            verb, obj = create.groups()
            noun = re.sub(r'^(?:统一|相关|专用)', '', obj)
            title, label, tags = verb+noun, '实施载体', []
            subject = subject or noun
        elif notify:
            obj, title = notify.groups()
            label, tags = '涉及对象', entities(obj)
        else:
            verb, targets = reserve.groups()
            tags = entities(targets)
            title, label, obj = verb+'资源', '涉及对象', '、'.join(tags[:2])
        steps.append(dict(title=title, method=clause+punctuation, method_label='执行方式',
                          tool_label=label, tool=obj, tags=tags))
    if len(steps) < 3 or any(len(step['tags']) < 2 for step in steps):
        return None
    for step in steps:
        tags = [re.sub(r'(?:等内容|成员)$', '', noun) for noun in step.pop('tags')[:2]]
        # Retain the noun or a short source compound ending with a known noun head.
        for i, tag in enumerate(tags):
            if len(tag) > 4:
                suffix = re.search(r'(.{2}(?:时间|人员|团队|信息|地点|数量|单位|清单|部门|日期))$', tag)
                if not suffix:
                    return None
                tags[i] = suffix[1]
        step.update(tag_a=tags[0], tag_b=tags[1])
    return initial[1], subject or steps[0]['title'], steps, end


class MaterialIndex:
    def __init__(self, root, catalog, theme):
        self.entries = []
        self.root = root
        self.theme = theme
        for e in catalog['layouts']:
            c = e.get('matching_contract') or {}
            if (e.get('asset_origin') or e['classification_status'] != 'verified'
                    or theme not in e['themes'] or c.get('policy') != 'structural'
                    or str(e.get('pptx_support', '')).startswith('blocked_')
                    or e.get('media_status') == 'missing-source-image'):
                continue
            counts, _ = count_profile(e, root)
            self.entries.append((e, c, counts))

    def candidates(self, relation, count):
        structures = {'ordered-steps': {'process', 'ordered-steps'}, 'comparison': {'comparison'},
                      'parallel-points': {'parallel-points', 'framework', 'summary'},
                      'single-focus': {'single-focus', 'summary'}}
        compatible = structures.get(relation, {relation})
        return [(e, c) for e, c, counts in self.entries if count in counts and
                ({c.get('structure_type'), *c.get('compatible_relations', [])} & compatible)]

    @lru_cache(maxsize=256)
    def capacity(self, relative):
        data = json.loads((self.root / relative).read_text(encoding='utf-8-sig'))
        limits = {}
        for field in data['fields']:
            role = (field.get('semantic_path') or '').rsplit('.', 1)[-1]
            if role not in ('heading', 'body') or not (field.get('semantic_path') or '').startswith(('items[','steps[')):
                continue
            width = field.get('max_width_units')
            limit = min(field.get('max_chars') or 100, int(width / 2) if width else 100)
            limits[role] = min(limits.get(role, 100), limit)
        return limits

    def interpret(self, raw, relation, count):
        """Lookup is completed with raw facts, before any slide title or summary exists."""
        pairs = comparison_facts(raw)
        steps = coordination_facts(raw)
        if pairs:
            relation = 'comparison'
        elif steps:
            relation = 'ordered-steps'
        if pairs:
            count = len(pairs)
        if steps:
            count = len(steps[2])
        candidates = self.candidates(relation, count)
        hits = [(e['id'], structural_required_paths(c, count)) for e,c in candidates]
        # Policy publication dates describe sources, not implementation phases.
        stage_evidence = re.search(r'第[一二三四五六\d]+阶段|分期实施|实施进度|建设排期', raw)
        if relation == 'parallel-points' and re.search(r'政策|通知|文号', raw) and not stage_evidence:
            hits = [(ident, paths) for ident, paths in hits if not any(
                re.search(r'(month|quarter|milestone|period)', path, re.I) for path in paths)]
        # Use limits from a source template for ordinary title/body composition too.
        budgets = []
        for entry, contract in candidates:
            if contract.get('item_fields') == ['title','body']:
                limits = self.capacity(text_binding_path(entry,self.theme,count))
                if limits.get('body',0) >= 14 and limits.get('heading',0) >= 3:
                    budgets.append((limits['body'], limits['heading']))
        view = None
        for _, paths in hits:
            paths = set(paths)
            if pairs and {'items[0].pair.center', 'items[0].left.first_body',
                          'items[0].right.second_body'} <= paths:
                rows = []
                for axis, left, right in pairs:
                    center = axis if len(axis) <= 2 else axis[:2] + '\n' + axis[2:]
                    rows.append({'pair': {'center': center},
                                 'left': dict(heading='变化前', first_body=left[0], second_body=left[1]),
                                 'right': dict(heading='变化后', first_body=right[0], second_body=right[1])})
                view = dict(type='comparison', items=rows)
                break
            if steps and {'steps[0].method', 'steps[0].tool', 'steps[0].tag_a', 'body.start_label'} <= paths:
                origin, noun, payload, end = steps
                view = dict(type='process', steps=payload, body=dict(title=noun,
                            start_label=origin, end_label=end), item_count=count)
                break
        return view, {'relation': relation, 'count': count, 'candidate_ids': [i for i, _ in hits],
                      'structured_from_source': view is not None,
                      'copy_budgets': sorted(set(budgets), reverse=True),
                      'copy_budget': max(budgets, default=None)}
