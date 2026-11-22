"""Prepare source-backed matching inputs while preserving the original page content."""
import argparse
import copy
import json
import re
from pathlib import Path

from relation_match import STRUCTURAL_ROLES
from text_width import visual_width_units

PARALLEL = {'parallel-points', 'summary', 'framework'}
STRUCTURAL = set(STRUCTURAL_ROLES)


def titled_items(items, titles):
    """Attach reviewed short titles to the original bodies in order."""
    if (not isinstance(items, list) or not items or not isinstance(titles, list)
            or len(titles) != len(items)
            or not all(isinstance(text, str) and text.strip() for text in [*items, *titles])):
        return None
    return [{'title': title.strip(), 'body': body} for title, body in zip(titles, items, strict=True)]


_CLAUSE_END = re.compile(r'[。；;，！？!?\n]|(?<!\d),|,(?!\d)')
_TITLE_FORM = re.compile(r'[\u3400-\u9fffA-Za-z0-9][\u3400-\u9fffA-Za-z0-9 +&/—·、-]*\Z')
_TITLE_BOUNDARY = re.compile(
    r'成立于|设在|位于|面向|聚焦|融合|提供|涵盖|包括|负责|参与|获得|入选|通过|'
    r'助力|赋能|提升|推进|推动|开展|需要|需确认|须确认|持续|不断|建议|核对|排查|'
    r'依据|依托|围绕|涉及|体现|影响|表明|显示|用于|形成|为准|采用|支持|配合|执行|'
    r'累计|同比|环比|预估|预计|约为|超过|达到|升至|降至|从未|先后|'
    r'(?:基本|全面)?覆盖|夯实|支撑|深化|做深|促进|只含|(?:详值)?见(?:原|附)|'
    r'所列|所处|所在|对接(?=\S)|设(?=额度|上限)|(?:须|还)?(?:确认|明确)|'
    r'较多|不足|出现|定期|实际召开|仍由|仍有|仍需|陆续|深耕|发放|未填(?:写)?|'
    r'分(?=账户|批次|区域)|按(?=两|每|日|月|年|规则|实际)|'
    r'的|及|为(?=[两三四五六七八九十\d])|[：:＝=]|'
    r'(?:近|约|超|仅|占|从|由)?[-−+]?\d[\d,]*(?:\.\d+)?余?'
    r'(?=[年月日万亿元省市区县人次个套%％点天笔项台家份载]|$|升|降)'
)
_TITLE_NOUN_END = re.compile(
    r'(?:方案|规划|计划|策略|目标|任务|咨询|流程|规定|规则|政策|制度|标准|口径|合同|协议|'
    r'企业|公司|总部|分部|部门|团队|学院|研究院|中心|网络|组织|平台|系统|软件|设备|'
    r'服务|产品|商品|项目|场景|业务|采购|招采|政务|建筑|建设|开发|研发|运营|宣传|'
    r'展示|推广|管理|维护|审核|审批|培训|申报|整改|验收|交付|监测|监管|修正|'
    r'内容|素材|资源|结构|能力|认证|荣誉|报告|汇总表|明细|清单|账户|指标|功能|词库|'
    r'记录|日志|会议|库存|账单|收益|损益|收入|支出|成本|薪酬|利润|买家|客户|用户|'
    r'面积|人数|销量|占比|额度|效率|进度|结余|余额|访问量|转化率|完成率|复购率|'
    r'单价|周期|差旅|租房|下架|上架|上线|上新|下单|产出物|住宿|宿舍|海报|易拉宝|奖|奖项|词条|缺口|'
    r'类目|分工|同步|销售|工地|流量|决策|引导|账务|账款|核算|对账|预算|考勤|唤醒|'
    r'开支|购买|质量|差距|修正值|单量|绩效|比重|偏好|利用率|准确率|'
    r'法律|操作|人员|员工|管理者|学员|教师|学生|职工|奖惩|影响力|质检|跟进|变化|补贴|'
    r'证书|著作权|专利|课题|配额|战略|体系|底座|资料|指南|偏差|估算|核实|闭环|应用|信息化|'
    r'达标率|合格率|采纳率|外勤率|检出率|达成率|出勤率|基线|保险|保障|开发商|提供商|'
    r'基金|材料|道路|教室|操场|讲座|比赛|演出|展览|图书|读物|标本|灌溉|土壤|物种|'
    r'片区|社区|公园|小区|街道|窗口|工厂|仓库|车辆|交通|供电|设施|建筑物|校区|'
    r'报名|登记|预约|条约|契约|桩|站|馆|库|厅|站点|时段|时效|摘要|搜索|样本|池|专区|奖学金)\Z'
)
_TITLE_TIME = re.compile(
    r'(?:上线[前后]|投产[前后]|开通[前后])|'
    r'(?:\d{4}年)?\d{1,2}月(?:\d{1,2}(?:日|[—–至-]\d{1,2}日))?(?:末|初)?|'
    r'(?:第[一二三四五六七八九十\d]+(?:阶段|季度|批次)|\d{4}年)'
)
_VAGUE_TITLES = set(
    '要点 内容 材料 情况 事项 问题 措施 工作 方面 其他 详情 说明 建议 结论 '
    '相关内容 具体情况 有关事项 以上内容 当前情况 仍有空间 示例 原文 '
    '公司 企业 部门 组织 团队 项目 平台 软件 服务 表格 数据 数字 数值 '
    '方式 方法 规则 口径 计划 任务 目标 结果 成果 能力 进度 时间 阶段 当前 '
    '可能 可以 需要 各项相关工作 相关人员 同期 月度 累计 日均 当月 上月'.split()
)
_CHUNK_PREFIX = re.compile(
    r'^(?:针对|为|由|向|和|及|与|须|系|仍|按|需|含|将|'
    r'让|仅|把|等|各个|部分|多数|逐步|一是|二是|以|日起|最终|上方|下方|'
    r'(?:连续|已有|已建|在建|获)?[\d一二三四五六七八九十]+[年月日天])'
)
_UNCERTAIN = re.compile(
    r'^(?:可能|应该|未能|尚未|暂无|没有|其余|该项|并且|以及|'
    r'相关事宜|待确认|请参考|详见|预计|如有|例如|应当|详值|有关事项)'
)
_NON_TITLE_END = re.compile(r'(?:的|及|和|与|或|仍|从|仅|由|并|起|超|约|为|获|前往|等|[-—])\Z')
_NUMBER_PREFIX = re.compile(
    r'^(?:\d{4}年|\d{1,2}月(?:\d{1,2}日)?(?:起|末)?|[-+−]?\d+(?:\.\d+)?[%％]|'
    r'(?:连续)?[一二三四五六七八九十\d]+余?年)\s*'
)
_NOUN_BEFORE_LINK = re.compile(
    r'正常|异常|较大|较好|须|需(?!求)|只|可(?=租|用|供|整合)|等|不(?:足|能|可)|'
    r'就绪|实际|平均|预计|尚未|未(?:能|完成)|可能|达标|存在|合计|偏高|截止|领军'
)
_TITLE_LEAD = re.compile(
    r'^(?:(?:连续)?[一二三四五六七八九十\d]+年获(?:得)?(?:中国|全国)?(?:领军|知名)?|'
    r'获(?:得)?(?:\d{4}年?)?|另有|其他|其中|当月|上月|'
    r'以制定|梳理|补充|更换|处理|调研|了解|制定|推进|再增|并|'
    r'该(?=[\u3400-\u9fff]{3,})|\d+[大家个项条名台套](?=[\u3400-\u9fff]))'
)
_AWARD_TITLE = re.compile(r'(?:科学技术奖|技术创新奖|应用创新奖|设计奖|贡献奖|教学成果奖)(?=[一二三四特]等奖|\Z)')
_APPLICATION_TOPIC = re.compile(r'(?:行业|企业|政务|农业|教育|工业|社区|医疗|交通)信息化(?=领军|建设|应用|\Z)')
_PLACEHOLDER_TITLE = re.compile(r'^(?:要点|条目|事项|内容|项目|第)\s*[0-9一二三四五六七八九十]+(?:项|条)?\Z')


def _title_candidates(body):
    scores = {}

    def add(value, score):
        title = value.strip(' \t\r《》“”「」"')
        if (title not in body or title in _VAGUE_TITLES or visual_width_units(title) > 16
                or not _TITLE_FORM.fullmatch(title) or len(title) < 2
                or not any(char.isalpha() for char in title) or _UNCERTAIN.match(title)
                or (_NON_TITLE_END.search(title) and not _TITLE_NOUN_END.search(title))
                or _PLACEHOLDER_TITLE.fullmatch(title)):
            return
        scores[title] = max(scores.get(title, 0), score)

    for match in re.finditer(r'简称\s*[“「《]?([\u3400-\u9fffA-Za-z][\u3400-\u9fffA-Za-z0-9 ]+)', body):
        add(match.group(1), 124)
    if match := _TITLE_TIME.match(body.lstrip()):
        add(match.group(), 78)

    for order, clause in enumerate(_CLAUSE_END.split(body)):
        clause = clause.strip()
        if not clause or _UNCERTAIN.match(clause):
            continue
        weight = max(0, 12 - 2 * order)
        if match := re.match(r'([^：:]+)[：:]', clause):
            explicit = match.group(1)
            if not re.search(r'\d+(?:人|次|元|个|天)\Z', explicit):
                add(explicit, 105 + weight)
        for pattern in (_AWARD_TITLE, _APPLICATION_TOPIC):
            if match := pattern.search(clause):
                add(match.group(), 70 + weight)
        enumeration = re.sub(r'^(?:还)?(?:包括|涵盖|包含)', '', clause)
        first_two = enumeration.split('、', 2)[:2]
        if len(first_two) == 2 and all(re.fullmatch(r'[\u3400-\u9fff]{2,5}', part) for part in first_two):
            if not any(_TITLE_BOUNDARY.search(part) for part in first_two):
                add('、'.join(first_two), 68 + weight)
        clause = _NUMBER_PREFIX.sub('', clause, count=1)
        # Keep complete chunks at clause, enumeration or predicate boundaries.
        for part, enumeration in enumerate(re.split(r'[、（）()]', clause)):
            chunks = _TITLE_BOUNDARY.split(_TITLE_LEAD.sub('', enumeration.strip()))
            for position, chunk in enumerate(chunks):
                candidate = _TITLE_LEAD.sub('', chunk.strip())
                if not candidate or _CHUNK_PREFIX.match(candidate):
                    continue
                prefix = _NOUN_BEFORE_LINK.split(candidate, maxsplit=1)[0]
                if prefix != candidate and _TITLE_NOUN_END.search(prefix):
                    add(prefix, 76 + weight - min(10, part + position))
                if _TITLE_NOUN_END.search(candidate):
                    add(candidate, 71 + weight - min(10, part + position) + min(7, len(candidate)))
    return sorted(scores, key=lambda title: -scores[title])


def infer_item_titles(items):
    """Extract a distinct, short source phrase for each item, or leave it for review."""
    if not isinstance(items, list) or not items or not all(isinstance(item, str) and item.strip() for item in items):
        return None
    candidates = [_title_candidates(item) for item in items]
    titles = [''] * len(items)
    used = set()
    for index in sorted(range(len(items)), key=lambda index: len(candidates[index])):
        title = next((title for title in candidates[index] if title not in used), None)
        if title is None:
            return None
        titles[index] = title
        used.add(title)
    return titles


def prepare(request, *, auto=False):
    if not isinstance(request, dict) or not isinstance(request.get('pages', []), list):
        raise ValueError('REQUEST_PAGES_INVALID')
    result = copy.deepcopy(request)
    changes, tasks, retained, matching_only, automatic = [], [], [], [], []
    auto = auto and result.get('auto_structure', True) is True
    for index, page in enumerate(result.get('pages', []), 1):
        if not isinstance(page, dict):
            raise ValueError('PAGE_INVALID: ' + str(index))
        content = page.get('content')
        if page.get('role') in STRUCTURAL or not isinstance(content, dict):
            continue
        info = {'page': index, 'page_id': page.get('page_id'),
                'title': page.get('title') or content.get('title'),
                'source_refs': page.get('source_refs', [])}
        reason = content.get('keep_bullets_reason')
        if isinstance(reason, str) and reason.strip():
            retained.append(dict(info, reason=reason))
            continue
        if auto:
            from layout_trials import infer_relation
            inferred = infer_relation(page, index)
            if inferred:
                relation, layout = inferred
                page.setdefault('items', content['items'])
                page['content'] = layout
                page['information_relation'] = relation
                evidence = dict(info, operation='infer_body_relation', relation=relation,
                                source_items=content['items'], body_preserved=True)
                page['content_preparation'] = evidence
                automatic.append(evidence)
                continue
        if auto and 'body_match' not in page and 'item_titles' not in content:
            annotation = automatic_annotation(page, content)
            if annotation is not None:
                page['body_match'] = annotation
                automatic.append(dict(info, annotation=annotation, body_preserved=True))
                continue
        if content.get('type') != 'bullets':
            continue
        items = content.get('items')
        if not isinstance(items, list) or not items:
            continue
        if 'body_match' in page:
            from content_adapters import matching_content
            _, note = matching_content(page)
            if note and note.startswith('body_match:'):
                matching_only.append(dict(info, operation=note, body_preserved=True))
                continue
        relation = page.get('matching_relation') or page.get('information_relation')
        titles = content.get('item_titles')
        cards = titled_items(items, titles)
        issue = None
        if relation not in PARALLEL:
            issue = 'RELATION_NEEDS_STRUCTURED_CONTENT'
        elif not all(isinstance(item, str) and item.strip() for item in items):
            issue = 'ITEMS_NEED_REVIEW'
        elif cards is None:
            issue = 'ITEM_TITLES_REQUIRED'
        if issue:
            tasks.append(dict(info, code=issue, information_relation=relation,
                              original_items=copy.deepcopy(items),
                              action=('依据材料明确顺序、层级或对比等关系，提交相应结构化内容；'
                                      '确需保留纯列表时填写 keep_bullets_reason。'
                                      if issue == 'RELATION_NEEDS_STRUCTURED_CONTENT' else
                                      '为每条原文提供对应 item_titles 短标题；保留 items 原文，'
                                      '不新增业务结论。确需纯列表时填写 keep_bullets_reason。')))
            continue
        content['type'] = 'cards'
        content['items'] = cards
        del content['item_titles']
        evidence = dict(info, operation='verbatim_bullets_to_cards',
                        body_preserved=True, title_review='host_agent_provided',
                        item_mapping=[{'source_path': f'pages[{index-1}].content.items[{i}]',
                                       'target_path': f'pages[{index-1}].content.items[{i}].body',
                                       'title': title.strip()}
                                      for i, title in enumerate(titles)])
        page['content_preparation'] = evidence
        changes.append(evidence)
    report = {'schema_version': 1,
              'status': 'needs_agent_structure' if tasks else 'ready_for_matching',
              'changed_pages': changes, 'tasks': tasks, 'retained_bullet_pages': retained,
              'scope': 'content organization only; no template fill or visual acceptance'}
    if matching_only:
        report['matching_only_pages'] = matching_only
    if auto:
        report['automatic_pages'] = automatic
    return result, report


def automatic_annotation(page, content):
    """Propose only structures that can be traced to the supplied page."""
    import re

    from content_adapters import infer_metric, infer_parallel_metrics, matching_content

    title = page.get('title') or content.get('title')
    if not isinstance(title, str) or not title.strip() or page.get('layout_id'):
        return None
    relation = page.get('matching_relation') or page.get('information_relation')
    items = content.get('items')
    annotation = None
    if relation == 'image-text' and content.get('type') == 'free_composition':
        annotation = {'type': 'image_gallery'}
    elif (content.get('type') == 'bullets' and isinstance(items, list) and items
          and all(isinstance(item, str) and item.strip() for item in items)):
        count = len(items)
        if relation == 'parallel-points' and 2 <= count <= 6:
            if titles := infer_item_titles(items):
                annotation = {'type': 'parallel_cards', 'item_titles': titles}
        elif relation in ('data', 'metrics') and count in (2, 3, 5, 6):
            groups = infer_parallel_metrics(items) if count in (5, 6) else None
            if groups and (len(groups), count) in ((4, 5), (2, 6)):
                annotation = {'type': 'parallel_metrics', 'groups': groups}
            elif not groups and (metric := infer_metric(items, title)):
                annotation = {'type': 'metric_evidence', 'metric': metric}
        elif relation == 'hierarchy' and count == 5:
            background = r'背景|现状|不足|差距|问题|面临|困难|瓶颈'
            methods = r'方法|流程|指南|标准|措施|机制|策略|路径'
            goal = r'目标|旨在|改善|提升|降低|确保|实现|促进|推动'
            if (all(re.search(background, item) for item in items[:2])
                    and all(re.search(methods, item) for item in items[2:4])
                    and re.search(goal, items[4])):
                annotation = {'type': 'text_hierarchy', 'groups': [
                    {'heading': '背景', 'indices': [0, 1]}, {'heading': '方法', 'indices': [2, 3]},
                    {'heading': '目标', 'indices': [4]}]}
        elif relation == 'single-focus' and count == 3:
            thesis = r'目标(?:是|为)|愿景(?:是|为)|旨在|致力于|力争|推动[^，。；]{2,18}发展'
            matches = [index for index, item in enumerate(items) if re.search(thesis, item)]
            if len(matches) == 1:
                annotation = {'type': 'single_focus', 'thesis_index': matches[0]}
        elif relation == 'data-table' and count == 5:
            if labels := infer_item_titles(items):
                annotation = {'type': 'report_table', 'columns': ['项目', '原文摘要'], 'row_labels': labels}
    if annotation is None:
        return None
    _, note = matching_content(dict(page, body_match=annotation))
    return annotation if note == f"body_match:{annotation['type']}" else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='Prepared request, or draft if tasks remain')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        paths = [args.request.resolve(), args.out.resolve(), args.report.resolve()]
        if len(set(paths)) != 3 or args.out.exists() or args.report.exists():
            raise ValueError('OUTPUT_PATH_CONFLICT')
        prepared, report = prepare(json.loads(args.request.read_text(encoding='utf-8-sig')), auto=True)
        for path, data in ((args.out, prepared), (args.report, report)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': report['status'], 'changed_pages': len(report['changed_pages']),
                          'pending_pages': len(report['tasks']), 'report': str(args.report)}, ensure_ascii=True))
        return 2 if report['tasks'] else 0
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'blocked', 'error_code': str(exc)[:300]}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
