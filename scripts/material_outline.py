"""Source units for Chinese case-study forms and paragraph-based Word documents."""
import re


def numbered(text):
    return [part.strip() for part in re.split(r'(?m)^\s*\d+[、.．]\s*', text)[1:] if part.strip()]


def sentences(text):
    return [s.strip() for s in re.split(r'[。；;\n]+', text) if s.strip()]


def units(section, kind, raw, rows, relation='parallel-points'):
    return dict(section=section, kind=kind, source=raw, rows=rows, relation=relation)


def parse_material(facts):
    paragraphs, cells = [], []
    for block in facts.get('blocks', []):
        if block['type'] == 'paragraph' and block['text'].strip():
            paragraphs.append(block['text'].strip())
        elif block['type'] == 'table':
            cells.extend('\n'.join(cell for cell in row if cell.strip()) for row in block['rows'])
    fields = {}
    current = None
    for cell in cells:
        m = re.fullmatch(r'[一二三四五六七八九十]+、(.+)', cell)
        if m:
            current = m[1]
        elif current:
            fields[current] = (fields.get(current, '') + '\n' + cell).strip()
    text = fields.get('案例还原', '')
    parts = re.split(r'【([^】]+)】', text)
    stages = {k:v.strip() for k,v in zip(parts[1::2], parts[2::2])}
    if not all(stages.get(k) for k in ('背景','任务','行动','成效','回顾')):
        # Keep document order for ordinary Word prose and split long lists at
        # source boundaries. A full deck needs at least two substantive units.
        passages=[]
        for block in facts['blocks']:
            if block['type']=='paragraph':
                if block['text'].strip():
                    passages.append(block['text'].strip())
            elif block['type']=='table':
                passages.extend('；'.join(cell for cell in row if cell.strip()) for row in block['rows'])
        if paragraphs and passages and paragraphs[0]==passages[0]:
            passages=passages[1:]
        if len(passages)==1:
            passages=sentences(passages[0])
        if len(passages)<2:
            raise ValueError('Word 仅含一个正文单元；请使用局部正文流程，或补充完整稿章节内容')
        blocks=[]
        for i, passage in enumerate(passages):
            lines=sentences(passage)
            for start in range(0,len(lines),4):
                group=lines[start:start+4]
                blocks.append(units('内容概览' if i==0 else '详细说明', '材料要点', passage, group))
        return paragraphs[:1], blocks
    setup, action, reuse = '建设背景', '实施过程', '成效复盘'
    blocks = []
    overview = fields.get('主题方向', '')
    pairs = [line for line in overview.splitlines() if re.match(r'在.+?(?:上|方面)[，,]', line)]
    if pairs:
        blocks.append(units(setup, '改造前后的变化', overview, pairs, 'comparison'))
    bg = numbered(stages['背景'])
    blocks.append(units(setup, '建设背景与政策依据', stages['背景'], bg or sentences(stages['背景'])))
    model = re.search(r'[“「]([^”」]+[+＋][^”」]+)[”」]([^。；，]+)', stages['背景'])
    if model:
        surrounding=next((p for p in sentences(stages['背景']) if model[0] in p),model[0])
        claim=re.search(r'(?:拟|将|要|旨在)(?:构建|建立|形成|打造)(.+)$',surrounding)
        blocks.append(dict(units(setup, '建设目标', surrounding, re.split(r'[+＋]', model[1]), 'framework'),
                           conclusion=('拟构建'+claim[1] if claim and '拟构建' in surrounding else model[0])))
    tasks = stages['任务']
    goal = re.search(r'(?:核心目标|总体目标)[：:]([^\n]+)', tasks)
    if goal:
        blocks.append(units(setup, '交付目标', goal[1], [goal[1]], 'single-focus'))
    todo = re.split(r'(?:困难与障碍|主要困难|难点)[：:]', tasks, maxsplit=1)
    planned = numbered(todo[0])
    if planned:
        blocks.append(units(setup, '具体建设任务', todo[0], planned))
    if len(todo)>1:
        blocks.append(units(action, '实施难点', todo[1], numbered(todo[1]) or sentences(todo[1])))
    for p in numbered(stages['行动']) or [stages['行动']]:
        blocks.append(units(action, '实施行动', p, sentences(p), 'ordered-steps'))
    blocks.append(units(reuse, '实施成效', stages['成效'], sentences(stages['成效'])))
    advice = numbered(fields.get('通用建议',''))
    for i in range(0,len(advice),3):
        group=advice[i:i+3]
        blocks.append(units(reuse, '通用建议', '\n'.join(group), group))
    review = stages['回顾']
    axes=re.search(r'通过([^。，]+?)[三四五六]位一体',review)
    blocks.append(units(reuse,'案例回顾',review,re.split(r'、|和|与',axes[1]) if axes else sentences(review),
                        'framework' if axes else 'parallel-points'))
    if axes:
        consequence=re.search(r'[，,]((?:实现|确保|保障)[^。；]+)',review[axes.end():])
        if consequence:
            blocks[-1]['conclusion']=consequence[1]
    return paragraphs, blocks
