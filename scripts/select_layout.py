"""Query the new catalog without loading all 324 records into model context."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from library_location import asset_root, get_library, load_catalog
from relation_match import load_taxonomy, match_relation, match_role
from plan_deck import count_profile, semantic_fit

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--library',type=Path);ap.add_argument('--role');ap.add_argument('--relation');ap.add_argument('--theme');ap.add_argument('--style');ap.add_argument('--source-page',type=int)
    ap.add_argument('--purpose');ap.add_argument('--item-count',type=int)
    ap.add_argument('--style-family');ap.add_argument('--allow-draft',action='store_true');ap.add_argument('--verified-only',action='store_true');ap.add_argument('--brief',action='store_true');ap.add_argument('--limit',type=int,default=20)
    a=ap.parse_args()
    if a.limit<1:ap.error('--limit必须大于0')
    if a.item_count is not None and a.item_count<1:ap.error('--item-count必须大于0')
    root=a.library or get_library();catalog=load_catalog(root)
    taxonomy=load_taxonomy(root,catalog)
    rows=[e for e in catalog['layouts'] if match_role(e,a.role,a.relation,taxonomy)
          and match_relation(e,a.relation,taxonomy)
          and (not a.theme or a.theme in e.get('themes',[]))
          and (not a.style or e.get('style')==a.style)
          and (not a.style_family or (e.get('style_family') or 'legacy-blue-red')==a.style_family)
          and (a.source_page is None or e.get('source_page')==a.source_page)
          and (a.allow_draft or e.get('status')=='approved')
          and (not a.verified_only or e.get('classification_status')=='verified')
          and (a.item_count is None or a.item_count in count_profile(e,root)[0])]
    rows.sort(key=lambda e: (e.get('classification_status')!='verified',
                             bool(a.relation and a.relation!=e.get('information_relation') and a.relation not in e.get('relation_aliases',[])),
                             bool(a.role and a.role!=e.get('role')),
                             -semantic_fit({'purpose':a.purpose or ''},e),
                             -int(a.item_count is not None and a.item_count==count_profile(e,root)[1]),
                             e['id']))
    rows=[dict(e, preview_root=str(asset_root(root,e))) if e.get('asset_origin') == 'skill' else e for e in rows]
    if a.brief:
        fields = ('id','role','style_family','information_relation','canonical_relation','search_label',
                  'classification_status','family_id','source_page','themes','style','visual_impact','preview','status')
        rows = [dict({k: e.get(k) for k in fields}, style_family=e.get('style_family') or 'legacy-blue-red',
                     **{k: e[k] for k in ('asset_origin','preview_root') if k in e}) for e in rows]
    print(json.dumps({'version':catalog['version'],'total_matches':len(rows),'shown_matches':min(len(rows),a.limit),
                      'matches':rows[:a.limit]},ensure_ascii=False,indent=2))
    return 0 if rows else 2
if __name__=='__main__':raise SystemExit(main())
