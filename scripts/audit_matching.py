"""Replay real page requests against one fixed knowledge-base checkout.

Planning and single-page fill are kept separate, so a recalled component is
never counted as reusable merely because it passed the catalog filter.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from body_header import body_components_enabled
from content_adapters import matching_content
from relation_match import STRUCTURAL_ROLE_ORDER
from candidate_trial import try_candidate
from plan_deck import load, resolve
from structure_content import prepare


def library_commit(library: Path) -> str:
    if (library / '.git').exists():
        return subprocess.check_output(['git', '-C', str(library), 'rev-parse', 'HEAD'], text=True).strip()
    manifest = json.loads((library / 'knowledge-manifest.json').read_text(encoding='utf-8-sig'))
    return manifest['source_commit']


def audit(library: Path, request_path: Path, work: Path, trial: bool) -> dict:
    request, content_preparation = prepare(json.loads(request_path.read_text(encoding='utf-8-sig')), auto=True)
    planning_request = dict(request)
    planning_request['allow_draft'] = request.get('asset_policy', 'verified_draft') != 'approved_only'
    planning_request['allow_provisional'] = request.get('asset_policy') == 'provisional_manual'
    catalog = load(library)
    entries = {entry['id']: entry for entry in catalog['layouts']}
    commit = library_commit(library)
    plan = resolve(library, planning_request, catalog=catalog)
    body_enabled = body_components_enabled(request)
    pages = []
    counters = Counter()
    for index, (source, choice) in enumerate(zip(request['pages'], plan['pages']), 1):
        is_body = source.get('role') not in STRUCTURAL_ROLE_ORDER
        if not is_body:
            continue
        counters['body_pages'] += 1
        counters['template_attempted'] += 1  # resolve examined every catalog entry
        candidate_ids = choice.get('candidate_ids', [])
        if candidate_ids:
            counters['eligible_pages'] += 1
        row = {'page': index, 'purpose': source['purpose'],
               'relation': source.get('information_relation') or
                           (source.get('content') or {}).get('type'),
               'candidate_ids': candidate_ids,
               'rejected_reasons': choice.get('rejected_reasons', {}),
               'normalization': choice.get('request_normalization', []),
               'trials': [], 'source_template_used': False}
        if trial and candidate_ids:
            content = dict(matching_content(source)[0])
            content['theme'] = request['theme']
            content['library_commit'] = commit
            if 'items' not in content and isinstance(source.get('items'), list):
                content['items'] = source['items']
            work.mkdir(parents=True, exist_ok=True)
            content_path = work / f'P{index:03d}-content.json'
            content_path.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
            for order, layout_id in enumerate(candidate_ids, 1):
                output = work / f'P{index:03d}-trial-{order}.pptx'
                trial_path = work / f'P{index:03d}-trial-{order}-content.json'
                filled, record = try_candidate(
                    library, entries[layout_id], content, source, content_path, trial_path, output,
                    allow_draft=planning_request['allow_draft'], body_header_pilot=body_enabled,
                    diagnostics=True)
                if 'detail' in record:
                    record['detail'] = record['detail'][:300]
                row['trials'].append(record)
                if filled is not None:
                    row['source_template_used'] = True
                    counters['trial_filled_pages'] += 1
                    if record.get('asset_origin') == 'skill':
                        counters['bundled_body_filled_pages'] += 1
                    break
                counters[record['reason_code']] += 1
            if not row['source_template_used']:
                counters['no_fit_after_trial_pages'] += 1
        pages.append(row)
    total = counters['body_pages']
    return {'request': str(request_path), 'library': str(library),
            'library_commit': commit,
            'content_preparation': content_preparation,
            'trial_enabled': trial, 'metrics': {
                'body_pages': total,
                'template_attempt_rate': counters['template_attempted'] / total if total else 0,
                'eligible_candidate_pages': counters['eligible_pages'],
                'eligible_candidate_rate': counters['eligible_pages'] / total if total else 0,
                'trial_filled_pages': counters['trial_filled_pages'] if trial else None,
                'bundled_body_filled_pages': counters['bundled_body_filled_pages'] if trial else None,
                'trial_pass_rate': counters['trial_filled_pages'] / counters['eligible_pages']
                                   if trial and counters['eligible_pages'] else None,
                'body_source_template_rate': counters['trial_filled_pages'] / total if trial and total else None,
                'trial_rejection_reasons': {key: value for key, value in counters.items()
                                            if key in ('MISSING_REQUIRED_FIELD', 'TEXT_OVER_CAPACITY',
                                                       'IMAGE_SLOT_MISMATCH', 'ITEM_COUNT_MISMATCH',
                                                       'TRIAL_REJECTED')},
            }, 'pages': pages}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--trial', action='store_true')
    args = parser.parse_args()
    if args.out.exists():
        parser.error('输出报告已存在')
    result = audit(args.library.resolve(), args.request.resolve(),
                   args.out.parent / (args.out.stem + '-trial'), args.trial)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result['metrics'], ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
