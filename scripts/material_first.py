"""Read Word, search the verified library, then assemble an editable page request."""
import re
from collections import Counter

from material_outline import parse_material, sentences
from material_retrieval import MaterialIndex, comparison_facts
from read_material import read
from structure_content import infer_item_titles


def excerpt(text, limit=43):
    """Choose complete source clauses. Never truncate a word or silently add an outcome."""
    clean = text.strip(' \n；。')
    if len(clean) <= limit:
        return clean
    clauses = [s.strip(' “”。；') for s in re.split(r'[，。；\n]|(?<=：)[“]', clean) if s.strip(' “”。；')]
    usable = [s for s in clauses if 3 <= len(s) <= limit and not s.endswith(('其中要求','的通知'))]
    # Introductory framing often consumes the entire short-copy budget.
    substantive = [s for s in usable if not re.match(
        r'近年来|按照.+要求|为了|针对.+(?:问题|痛点)$|依托该体系$|20\d\d年\d+月$', s)]
    substantive = [re.sub(r'^其中要求[“「]?|^提出要', '', s) for s in substantive]
    pool = [x for x in substantive if not re.fullmatch(r'依托(?:于)?[^。]+(?:设备|体系)|针对[^。]+(?:问题|痛点)',x)] or substantive or usable
    if not pool:
        return clean
    useful = [x for x in pool if re.search(r'推进|优化|提高|实行|统一纳入|实现|确保|达到|扩大|明确|协调|留痕', x)]
    first = (useful[0] if len(clean)>120 and useful else pool[0])
    for other in pool[pool.index(first)+1:]:
        if len(first) + len(other) + 1 <= limit:
            first += '，' + other
        else:
            break
    return first


def action_title(text, limit):
    # A short verb + its actual object reads better than a numbered placeholder.
    verbs = r'明确|梳理|捋顺|核对|整理|绘制|建立|形成|准备|申请|培训|协调|开展|配置|部署|安装|上报|规划|调试|分配'
    for clause in re.split(r'[，。；、]',text):
        verb = re.search(verbs, clause)
        if not verb:
            continue
        objects = re.findall(r'需求|手册|端口|设备|程序|文件|环境|材料|团队|信息|人员|任务|工位|系统|清单|网络|场地|工期|图表',clause[verb.end():])
        if objects and len(verb[0]+objects[-1]) <= limit:
            return verb[0]+objects[-1]
        if re.search(r'(?:可进行|支持|采用)(.{2,5})化(.{2})$',clause):
            match=re.search(r'(?:可进行|支持|采用)(.{2,5})化(.{2})$',clause)
            if len(match[1]+match[2])<=limit:
                return match[1]+match[2]
    for clause in re.split(r'[，。；、]', text):
        for match in re.finditer('('+verbs+r')([^的，。；、]{1,14})',clause):
            verb, obj = match.groups()
            obj=re.sub(r'^(?:不同的?|相关|临时|统一|新增|增加|好|至|进行)', '',obj)
            if re.fullmatch(r'[\u4e00-\u9fffA-Za-z0-9]{2,}',obj) and len(verb+obj)<=limit:
                return verb+obj
    action = re.search(r'(?:明确|梳理|核对|捋顺|整理|绘制|建立|形成|准备|申请|培训|协调|开展|批量化配置|部署|安装|上报|规划|调试|分配)',text)
    return action[0] if action and len(action[0])<=limit else ''


def cards(rows, kind, budget=None):
    body_limit, head_limit = budget or (43, 10)
    body_limit,head_limit=min(body_limit,43),min(head_limit,12)
    items=[]
    for i,row in enumerate(rows,1):
        head, sep, rest = row.partition('\n')
        if sep and kind=='通用建议':
            title = re.split('[，。]',head)[0]
            body = rest
        elif m := re.match(r'^([^：:\n]{2,15})[：:]\s*(.+)',row,re.S):
            title,body=m.groups()
        else:
            title,body='',row
        if not title:
            first=re.split(r'[，；。 、（(]',row)[0]
            suggestion=infer_item_titles([row])
            title=first if 2<=len(first)<=10 else suggestion[0] if suggestion else ''
        if not title or title.startswith(kind):
            noun = re.search(r'(?:^|[、，]|不同的|相关|各类|不同|明确)([\u4e00-\u9fffA-Za-z0-9]{2,9}(?:系统|需求|平台|信息|设备|手册|工位|程序|配置|操作))(?=的|及|及其|，|。|部署|等|$)',row)
            if noun:
                title=noun[1]
            elif '的' in row:
                short = re.split(r'的',row,1)[0]
                if 2<=len(short)<=10:
                    title=short
        if kind == '实施行动' or len(title)>head_limit or not title:
            title=action_title(row,head_limit) or title
        if kind=='通用建议' and sep:
            title=re.split('[，。]',head)[0]
            head_limit=max(head_limit,min(12,len(title)))
        if len(title)>head_limit or not title:
            title=f'步骤{i}' if kind=='实施行动' else f'要点{i}'
        if any(it['title']==title for it in items):
            title = next((p for p in re.split(r'[，。、；]',row)
                          if 2<=len(p)<=head_limit and p!=title and all(it['title']!=p for it in items)), f'要点{i}')
        if re.search(r'(?:其中要求|明确要求)[“「]',body):
            quote=re.search(r'(?:其中要求|明确要求)[“「]([^”」]+)',body)[1]
            stamp=re.search(r'\d{4}年\d{1,2}月',body)
            detail=(stamp[0]+'：' if stamp else '')+excerpt(quote,max(17,body_limit-8))
        else:
            detail=excerpt(body,body_limit)
        items.append({'title':title,'body':detail})
    return items


def prepare_body(unit, index, occurrence, previous_search):
    raw=unit['source']
    kind,relation,rows=unit['kind'],unit['relation'],unit['rows']
    if relation=='ordered-steps' and 2 <= len(rows) <= 4:
        for pos in sorted(range(len(rows)),key=lambda i:-len(rows[i])):
            parts=re.split(r'，(?=统一上报|申请|提供|形成|由[^，]{1,12}出面)',rows[pos],maxsplit=1)
            if len(parts)==2:
                rows=rows[:pos]+parts+rows[pos+1:]
                break
    view,search=index.interpret(raw,relation,len(rows))
    relation=search['relation']
    if (previous_search and previous_search['relation']==relation and previous_search['count']==search['count']
            and len(search['copy_budgets'])>1 and search['copy_budget']==previous_search['copy_budget']):
        # Give a distinct reviewed capacity profile a chance before fixing copy.
        search['copy_budget']=search['copy_budgets'][1]
    title=kind
    content=None
    if view and relation=='comparison':
        content={'type':'cards','items':[dict(title=t,body='、'.join(l)+' → '+'、'.join(r))
                                         for t,l,r in comparison_facts(raw)]}
    elif view and 'steps' in view:
        title=view['body']['title']+'与实施准备'
        content={'type':'process','items':[dict(title=row['title'],body=row['method']) for row in view['steps']]}
    elif kind=='交付目标':
        # Distinguish a deadline from the equipment and software covered by it.
        m=re.search(r'^(.{1,12}?)(?:时间)?内完成(.+?的[^，。]+)[，,]以及(.+?)[，,](达到[^。]+)',raw)
        if m:
            lead=dict(title=m[1]+'内',body=m[4])
            content={'type':'priority_grid','variant':'summary_split','lead':lead,
                     'support':[dict(title='到货安装',body=m[2]),dict(title='部署调试',body=m[3])]}
        else:
            content={'type':'bullets','items':sentences(raw)}
    elif relation=='framework':
        title=kind
        context=unit.get('conclusion')
        if context:
            for quoted in re.findall(r'[“「]([^”」]+)[”」]', context):
                if re.split(r'[+＋]', quoted)==rows:
                    context=context.replace('“'+quoted+'”','')
        content=({'type':'bullets','variant':'lead','featured_index':0,'items':[context,*rows]}
                 if context and len(context)<=16 and len(rows)<6 else {'type':'bullets','items':rows})
        content['keep_bullets_reason']='原文给出同级概念，按原顺序展示'
    else:
        items=cards(rows, kind, search['copy_budget'])
        if relation=='ordered-steps':
            goal = re.search(r'(?:明确|提升|形成|完成)([^。，、]{3,16})(?=[。；，]|$)', raw)
            title = re.sub(r'^不同的|^相关','',goal[1]) if goal else items[0]['title']+'实施步骤'
        if kind=='通用建议':
            title=f'通用建议（{occurrence}）'
        content={'type':'process' if relation=='ordered-steps' else 'cards','items':items}
    content['title']=title
    page=dict(role='body',title=title,purpose=title,information_relation=relation,
              content=content,source_refs=[unit['section']+'／'+kind],
              material_excerpt=raw)
    if view:
        view.update(title=title)
        # One semantic payload for the whole pool. No component ID is submitted.
        page.update(material_matching_content=view,matching_relation=relation,needs={'item_count':search['count']})
    if relation=='ordered-steps' and not view:
        # Preserve the complete set of extracted actions even for dense columns.
        if len(content['items'])>5:
            page['content']={'type':'rule_list','title':title,'items':cards(unit['rows'],kind)}
    return page,search


def structure(role,title,**fields):
    return {'role':role,'title':title,'purpose':title,'content':fields}


def build(path, root, catalog, theme='blue'):
    material=read(path)
    if material['kind']!='docx':
        raise ValueError('直接出稿入口需要 Word 文档')
    paragraphs,units=parse_material(material)
    if not units:
        raise ValueError('未找到可出稿正文')
    index=MaterialIndex(root,catalog,theme)
    title=paragraphs[0] if paragraphs else path.stem
    author=next((re.sub(r'[_\s]','',p.split('：',1)[-1]) for p in paragraphs if p.startswith('作者：')), '')
    # Split an organization from its subject only at a complete organization name.
    split=re.match(r'^(.+?(?:中心|公司|委员会|办公室|集团|研究院))(.{2,24})$',title)
    subject=split[2] if split else title
    cover=dict(title=subject,subtitle=split[1] if split else '',presenter=('分享人：'+author if author else ''),
               english_title='EPOINT',english_subtitle='CASE SHARING')
    pages=[structure('cover',subject,cover=cover,texts={'cover.'+k:v for k,v in cover.items() if v})]
    sections=list(dict.fromkeys(u['section'] for u in units))
    contents=[dict(title=sec,subtitle=next(u['kind'] for u in units if u['section']==sec)) for sec in sections]
    pages.append(dict(structure('directory','分享目录',title_text='分享目录',page={'title':'分享目录'},items=contents,
                                texts={'page.title':'分享目录'}),items=contents,needs={'item_count':len(sections)}))
    trace=[]
    seen=Counter()
    for n,section in enumerate(sections,1):
        texts={'section.number':f'{n:02d}','section.title':section}
        pages.append(structure('section',section,section={'number':f'{n:02d}','title':section},texts=texts))
        previous_search=None
        for unit in (u for u in units if u['section']==section):
            seen[unit['kind']]+=1
            page,search=prepare_body(unit,index,seen[unit['kind']],previous_search)
            previous_search=search
            pages.append(page)
            trace.append(dict(page=len(pages),source=unit['source'],**search))
    pages.append(structure('closing','谢谢交流',closing={'title':'谢谢交流','presenter':cover['presenter']},
                           texts={'closing.title':'谢谢交流','closing.presenter':cover['presenter']}))
    request={'theme':theme,'style_family':'deep-blue-tech' if theme=='deep-blue-tech' else 'legacy-blue-red',
             'format':'pptx','complete_deck':True,'pages':pages}
    return request,{'source':str(path),'sha256':material['sha256'],'warnings':material['warnings'],
                    'order':['read_word','retrieve_by_source_relation_and_count','draft_page','plan_and_trial'],
                    'pages':trace}
