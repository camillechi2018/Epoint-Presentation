"""Check a planned PPTX against content, structure and deck-level rules."""
import argparse,json,re
from pathlib import Path
from pptx import Presentation

from relation_match import STRUCTURAL_ROLES
from tech_background import uses_shared_tech_background
from body_background import blue_red_background_issue, uses_component_atmosphere
from layout_safety import walk_shapes

SKILL=Path(__file__).resolve().parents[1]

def audit(plan_path,pptx_path):
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8-sig'));p=Presentation(pptx_path)
    offline_layout=json.loads((SKILL/'assets/layouts/offline-core.json').read_text(encoding='utf-8-sig'))
    brand=json.loads((SKILL/'assets/brand/brand-baseline.json').read_text(encoding='utf-8-sig'))
    issues=[];pages=plan.get('pages',plan.get('slides'))
    if not isinstance(pages,list) or not pages:raise ValueError('验收清单须提供页面')
    require_templates=plan.get('require_template_source',False)
    commit=plan.get('library_commit','')
    has_mandatory=any(isinstance(x,dict) and x.get('role') in STRUCTURAL_ROLES for x in pages)
    if (require_templates or has_mandatory) and (not isinstance(commit,str) or not re.fullmatch(r'[0-9a-f]{40}',commit)):
        raise ValueError('必用知识库页面的来源验收须提供完整 library_commit')
    def add(level,slide,code,detail):issues.append({'severity':level,'slide':slide,'code':code,'detail':detail})
    if len(p.slides)!=len(pages):add('P0',0,'page_count',f'计划{len(pages)}页，成稿{len(p.slides)}页')
    seen=[]
    for n,slide in enumerate(p.slides,1):
        info=pages[n-1] if n<=len(pages) else {}
        theme = plan.get('theme')
        drawn = info.get('selection_mode') in {'guided_composition', 'free_composition'}
        shapes = list(slide.shapes)
        rules = [shape for shape in shapes if shape.name == 'brand:content-rule']
        if theme in ('blue', 'red') and (drawn or info.get('body_header')) and len(rules) != 1:
            add('P0', n, 'body_rule_count', '通用页眉须恰有一条分割线')
        for rule in rules:
            effects = rule._element.xpath('.//a:effectRef')
            shadow = rule._element.xpath('.//a:outerShdw | .//a:innerShdw | .//a:prstShdw')
            if shadow or any(ref.get('idx') != '0' for ref in effects) or (
                    not effects and not rule._element.xpath('./p:spPr/a:effectLst')):
                add('P0', n, 'body_rule_shadow', '页眉分割线存在阴影或未显式关闭主题效果')
        if info.get('body_header',{}).get('background') == 'skill_tech' and not uses_shared_tech_background(slide,offline_layout):
            add('P0',n,'body_component_tech_background','知识库纯正文未使用科技风公共背景')
        if drawn or uses_component_atmosphere(offline_layout, info.get('layout_id'), theme):
            tech_header=theme=='deep-blue-tech'
            if tech_header:
                if not uses_shared_tech_background(slide,offline_layout):
                    add('P0',n,'new_drawn_tech_background','新绘正文未使用科技风公共背景')
                if not shapes or shapes[0].shape_type!=6:
                    add('P0',n,'new_drawn_tech_header','科技风原生标题栏图形组缺失')
            else:
                issue=blue_red_background_issue(shapes,offline_layout,theme,brand['themes'].get(theme))
                if issue:
                    add('P0',n,*issue)
        if info.get('role') in STRUCTURAL_ROLES and info.get('selection_mode') != 'source_template':
            add('P0',n,'structural_source','结构页必须使用知识库模板')
        if require_templates or info.get('role') in STRUCTURAL_ROLES:
            actual=slide._element.cSld.get('name','')
            expected=info.get('source_stamp')
            prefix=f"epoint:{info.get('layout_id')}:{plan.get('theme')}:"
            if not isinstance(expected,str) or not expected.startswith(prefix) or not expected.endswith(f':{commit}') or actual!=f'{expected}:{n}':
                add('P0',n,'template_source','成稿页的模板、主题、原稿页或知识库版本与清单不一致')
        texts=[sh.text.strip() for sh in walk_shapes(slide.shapes) if sh.has_text_frame and sh.text.strip()]
        joined=' '.join(texts)
        if re.search(r'\[.{1,25}\]|单击添加|点击添加|汇报人：WPS|金山办公软件',joined):add('P0',n,'placeholder_or_source_example','发现占位或源模板示例文字')
        if info.get('role')=='data-chart' and not info.get('data_source'):add('P0',n,'chart_source','计划缺少图表数据来源')
        if info.get('image_sources') and any(not str(x).strip() for x in info['image_sources']):add('P0',n,'image_source','图片来源为空')
        if n>1 and info.get('layout_id') and info.get('layout_id')==pages[n-2].get('layout_id'):
            add('P1',n,'repeated_layout','与上一页使用相同组件，需检查节奏')
        seen.append(info.get('role'))
    for n in range(3,len(seen)+1):
        if seen[n-3:n]==['data-chart']*3:add('P1',n,'dense_sequence','连续三页数据图，需目视检查节奏')
    if plan.get('complete_deck') is True:
        if (pages[0].get('role')!='cover' or pages[-1].get('role')!='closing'
                or 'directory' not in seen or 'section' not in seen):
            add('P0',0,'complete_deck_roles','完整演示稿须包含封面、目录、章节、封底')
        elif seen.index('directory')>=seen.index('section'):
            add('P0',0,'complete_deck_order','目录须位于首张章节页之前')
        section_layouts={page.get('layout_id') for page in pages if page.get('role')=='section'}
        if len(section_layouts)!=1 or None in section_layouts:
            add('P0',0,'section_layout_mixed','同一完整演示稿的章节页须使用同一组件版式')
    checks = ['page_count', 'body_rule_count', 'body_rule_shadow', 'new_drawn_background',
              'component_atmosphere', 'placeholder_or_source_example', 'chart_source',
              'image_source', 'repeated_layout', 'dense_sequence']
    if require_templates or has_mandatory:
        checks.insert(0, 'template_source')
    return {'schema_version':'1.0','slide_count':len(p.slides),'planned_count':len(pages),'issues':issues,'p0_passed':not any(x['severity']=='P0' for x in issues),'checks':checks,'manual_review_required':['PowerPoint实际文字边界与箭头碰撞','中文断行、字号、底部留白与相邻页面疏密','图片裁切及图表编辑数据','事实、术语与品牌核对']}
def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=audit(a.plan,a.input);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'p0_passed':result['p0_passed'],'issues':len(result['issues'])},ensure_ascii=False))
    if not result['p0_passed']:raise SystemExit(2)
if __name__=='__main__':main()

