"""Portable, auditable entry for knowledge-base preflight and page planning."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from library_location import SKILL, load_catalog, resolve_library, selection_label
from font_profile import probe as probe_font_profile
from office_runtime import probe as probe_office, assemble as assemble_office
from delivery_status import assess as assess_delivery, exit_code as delivery_exit_code
from assembly_backend import BACKENDS, select_backend
from relation_match import STRUCTURAL_ROLE_ORDER as STRUCTURAL
from body_header import body_components_enabled
from content_adapters import matching_content, unmapped_title_body_fields
import atomic_body
from layout_trials import layout_key, retains_text, text_fields, trial_alternative


def _load_workflow():
    # Environment inspection and library preflight must not require rendering packages.
    global resolve, summarize_selection, try_candidate, render_guided_page
    global resolved_variant, validate_page, fallback_type, audit_deck
    global check_structure, check_directory_section_count, directory_item_count, check_prefilled, check_finished
    from plan_deck import resolve, summarize_selection
    from candidate_trial import try_candidate
    from render_offline_brand import render as render_guided_page, resolved_variant, validate_page
    from fallback_rules import fallback_type
    from audit_deck import audit as audit_deck
    from delivery_gate import (check_structure, check_directory_section_count,
                               directory_item_count, check_prefilled, check_finished)

STYLES = {
    'blue': 'legacy-blue-red',
    'red': 'legacy-blue-red',
    'deep-blue-tech': 'deep-blue-tech',
}

def error_code(exc):
    value = str(exc).casefold()
    if 'hash' in value or '哈希' in value or '清单' in value:
        return 'LIBRARY_HASH_FAILED'
    if 'authentication' in value or 'permission denied' in value or '403' in value or '认证' in value:
        return 'GIT_AUTH_FAILED'
    if 'git' in value or 'fetch' in value or '网络' in value or 'resolve host' in value:
        return 'GIT_UNAVAILABLE'
    return 'LIBRARY_UNAVAILABLE'


def safe_message(exc):
    message = str(exc)
    return re.sub(r'https://[^\s/@]+:[^\s/@]+@', 'https://[REDACTED]@', message)[:400]


def style_assets(theme):
    root = SKILL / 'assets' / 'style-kits' / theme
    manifest = SKILL / 'assets' / 'style-kits' / 'manifest.json'
    if not manifest.is_file():
        return {'ready': False, 'reason': 'STYLE_KIT_MISSING'}
    data = json.loads(manifest.read_text(encoding='utf-8'))
    profile = root / 'style.json'
    if not profile.is_file():
        return {'ready': False, 'reason': 'STYLE_PROFILE_MISSING'}
    images = [(SKILL / rel).resolve() for rel in data.get('styles', {}).get(theme, {}).get('previews', [])]
    records = json.loads(profile.read_text(encoding='utf-8'))['sample_records']
    hashes_ok = all((root / row['preview']).is_file() and
                    hashlib.sha256((root / row['preview']).read_bytes()).hexdigest() == row['sha256'] for row in records)
    return {'ready': bool(images) and all(x.is_file() for x in images) and hashes_ok,
            'version': data.get('version'), 'style_path': str(profile.resolve()),
            'preview_paths': [str(x) for x in images],
            'visual_references_loaded': False,
            'reason': None if hashes_ok else 'STYLE_PREVIEW_HASH_FAILED'}


def capability(assembly_backend='auto'):
    selected = select_backend(assembly_backend)
    windows = platform.system() == 'Windows'
    com = importlib.util.find_spec('win32com') is not None if windows else False
    backend = probe_office() if windows and selected == 'powerpoint' else {'status': 'not_probed'}
    registry = backend['status'] == 'detected'
    shell = shutil.which('pwsh') or shutil.which('powershell')
    native = all(importlib.util.find_spec(name) is not None for name in ('pptx', 'PIL', 'lxml'))
    return {
        'assembly_backend': selected, 'native_backend_available': native,
        'python': sys.version.split()[0], 'git': shutil.which('git'),
        'python_pptx': importlib.util.find_spec('pptx') is not None,
        'pillow': importlib.util.find_spec('PIL') is not None,
        'powerpoint_com_module': com,
        'powerpoint_registry': registry, 'powershell': shell, 'office_backend': backend,
        'can_plan': True,
        'can_fill_pptx': importlib.util.find_spec('pptx') is not None,
        'can_assemble_pptx': native if selected == 'native' else windows and registry and bool(shell),
        'can_render_in_powerpoint': windows and registry and bool(shell),
    }


def candidate_counts(root, theme, family):
    catalog = load_catalog(root)
    counts = {}
    for role in (*STRUCTURAL, 'body'):
        rows = [e for e in catalog['layouts']
                if theme in e.get('themes', [])
                and (e.get('style_family') or 'legacy-blue-red') == family
                and (e.get('role') == role if role != 'body' else e.get('role') not in STRUCTURAL)
                and not str(e.get('pptx_support', '')).startswith('blocked_')
                and e.get('media_status') != 'missing-source-image']
        counts[role] = {'verified_draft': sum(e.get('classification_status') == 'verified' and e.get('status') == 'draft_pending_review' for e in rows),
                        'approved': sum(e.get('classification_status') == 'verified' and e.get('status') == 'approved' for e in rows),
                        'unverified': sum(e.get('classification_status') != 'verified' for e in rows)}
    return counts


def preflight(request, *, library=None, offline=False, native_experimental=False,
              assembly_backend='auto'):
    selected = select_backend(assembly_backend, legacy_native=native_experimental)
    theme = request.get('theme', 'blue')
    if theme not in STYLES:
        raise ValueError('theme 仅支持 blue、red、deep-blue-tech')
    family = request.get('style_family', STYLES[theme])
    if family != STYLES[theme]:
        raise ValueError('theme 与 style_family 不一致')
    fmt = request.get('format', 'pptx')
    if fmt not in ('pptx', 'html'):
        raise ValueError('format 仅支持 pptx 或 html')
    complete = request.get('complete_deck', True)
    if not isinstance(complete, bool):
        raise ValueError('complete_deck 必须是布尔值')
    policy = request.get('asset_policy', 'verified_draft')
    if policy not in ('verified_draft', 'approved_only', 'provisional_manual'):
        raise ValueError('asset_policy 不受支持')
    result = {'schema_version': '1.0', 'status': 'blocked', 'error_code': None,
              'theme': theme, 'style_family': family, 'format': fmt,
              'complete_deck': complete, 'asset_policy': policy,
              'skill_version': _skill_version(), 'library_connected': False,
              'library_used': False, 'library_source': None, 'library_commit': None,
              'style_kit': style_assets(theme), 'runtime': capability(selected),
              'assembly_backend': selected,
              'candidate_counts': None, 'warnings': []}
    if native_experimental:
        result['warnings'].append('--native-experimental 已兼容映射为 --assembly-backend native；'
                                  'macOS/Linux 默认自动选择原生组装')
    if selected == 'native':
        result['warnings'].append('原生组装不依赖 Office；生成与应用验证分开记录，'
                                  'LibreOffice 预览不等于 PowerPoint 视觉签收')
    root = None
    try:
        if library:
            root, source, commit, warning = resolve_library(library)
        elif offline:
            root, source, commit, warning = resolve_library(cache_only=True)
        else:
            root, source, commit, warning = resolve_library()
        result.update(library_connected=True, library_source=source, library_commit=commit,
                      library_path=str(root), candidate_counts=candidate_counts(root, theme, family))
        if warning:
            result['warnings'].append('远端更新失败，已使用最后一次校验通过的本地来源：' + safe_message(warning))
    except (RuntimeError, FileNotFoundError, ValueError, OSError) as exc:
        result['error_code'] = error_code(exc)
        result['warnings'].append(safe_message(exc))
    if not result['style_kit']['ready']:
        result['error_code'] = result['style_kit']['reason'] or 'STYLE_KIT_MISSING'
        return result
    if root:
        counts = result['candidate_counts']
        requested_roles = {'cover', 'closing'}
        if isinstance(request.get('pages'), list):
            requested_roles.update(page.get('role') for page in request['pages'] if isinstance(page, dict))
        missing = [role for role in STRUCTURAL if role in requested_roles and counts[role]['verified_draft'] + counts[role]['approved'] == 0]
        if fmt == 'html':
            result['error_code'] = 'HTML_TEMPLATE_UNVERIFIED'
        elif policy == 'approved_only' and any(counts[role]['approved'] == 0 for role in requested_roles if role in STRUCTURAL):
            result['error_code'] = 'APPROVED_TEMPLATE_MISSING'
        elif missing and complete:
            result['error_code'] = 'NO_' + theme.upper().replace('-', '_') + '_' + missing[0].upper() + '_VERIFIED'
        elif complete and not result['runtime']['can_fill_pptx']:
            result['error_code'] = 'PPTX_FILL_BACKEND_UNAVAILABLE'
        elif complete and not result['runtime']['can_assemble_pptx']:
            result['error_code'] = 'PPTX_BACKEND_UNAVAILABLE'
        else:
            result['status'] = 'ready' if complete else 'partial_draft'
            result['error_code'] = None
    if result['status'] == 'blocked' and not complete and result['style_kit']['ready']:
        result['status'] = 'partial_draft'
    result['can_make_complete_deck'] = result['status'] == 'ready'
    return result


def preview_covers(library, request, catalog, output, *, theme, style_family):
    from cover_gallery import build_cover_gallery

    cover = next((page for page in request.get('pages', []) if page.get('role') == 'cover'), None)
    if cover is None:
        warning = '逐页请求中没有封面页。'
    else:
        try:
            cover = dict(cover, theme=theme, style_family=style_family)
            plan = resolve(library, dict(request, pages=[cover]), catalog=catalog,
                           candidate_summary_limit=None)
            return build_cover_gallery(library, plan['pages'][0], output)
        except (OSError, ValueError) as exc:
            warning = safe_message(exc)
    return {'status': 'unavailable', 'image_path': None, 'candidates': [], 'warnings': [warning]}


def _skill_version():
    text = (SKILL / 'SKILL.md').read_text(encoding='utf-8-sig')
    match = re.search(r'version:\s*["\']?([^"\'\s]+)', text)
    return match.group(1) if match else 'unknown'


def execute_plan(request, plan, report, output: Path, *, catalog=None):
    """Fill each planned page, assemble it and audit mandatory source pages."""
    from capacity_preflight import LayoutMetadata
    _load_workflow()
    if not report['can_make_complete_deck'] or request.get('format', 'pptx') != 'pptx':
        raise ValueError('预检未通过完整 PPTX 出稿门槛')
    if output.exists():
        raise FileExistsError('成稿文件已存在，请另存新文件')
    pages = request.get('pages', [])
    if len(pages) != len(plan['pages']):
        raise ValueError('逐页内容与规划页数不一致')
    check_directory_section_count(pages)
    check_structure([dict(choice, role=page.get('role'))
                     for page, choice in zip(pages, plan['pages'])], complete=True)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep failed-run evidence, but never reuse its partial page files on retry.
    work = Path(tempfile.mkdtemp(prefix=output.stem + '-work-', dir=output.parent))
    report['execution_work_dir'] = str(work)
    slides = []
    audit_pages = []
    office_timeout = request.get('office_timeout_seconds', 300)
    if type(office_timeout) is not int or not 1 <= office_timeout <= 3600:
        raise ValueError('OFFICE_TIMEOUT_INVALID')
    used_guided_variants = {}
    actual_layouts = []
    locked_section_layout_id = None
    entries = {entry['id']: entry for entry in catalog['layouts']} if catalog is not None else None
    body_enabled = body_components_enabled(request)
    metadata = LayoutMetadata()
    allow_draft = request.get('asset_policy', 'verified_draft') != 'approved_only'
    for index, (page, choice) in enumerate(zip(pages, plan['pages']), 1):
        content = page.get('content')
        if not isinstance(content, dict):
            raise ValueError(f'第 {index} 页缺少可填充的 content 对象')
        inferred = (page.get('content_preparation') or {}).get('operation') == 'infer_body_relation'
        if inferred:
            choice['inferred_relation'] = page['information_relation']
        page_out = work / f'P{index:03d}.pptx'
        if page_out.exists():
            raise FileExistsError(f'中间文件已存在：{page_out}')
        if choice['selection_mode'] == 'source_template':
            library = Path(report['library_path'])
            if entries is None:
                entries = {entry['id']: entry for entry in load_catalog(library)['layouts']}
            data = dict(matching_content(page)[0])
            data['theme'] = report['theme']
            data['library_commit'] = report['library_commit']
            if 'items' not in data and isinstance(page.get('items'), list):
                data['items'] = page['items']
            content_path = work / f'P{index:03d}-content.json'
            content_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            filled = None
            candidate_ids = choice.get('candidate_ids', [choice['layout_id']])
            if page.get('role') == 'section' and locked_section_layout_id:
                candidate_ids = [locked_section_layout_id]
                choice['candidate_ids'] = candidate_ids
            # Prefer a different verified template before trying a drawn layout.
            previous_id = actual_layouts[-1] if actual_layouts else None
            repeat_search = (previous_id and candidate_ids and previous_id == candidate_ids[0]
                             and not page.get('layout_id') and page.get('role') not in STRUCTURAL)
            if repeat_search:
                candidate_ids = sorted(candidate_ids, key=lambda ident: ident == previous_id)
            for candidate_id in candidate_ids:
                trial_path = work / f'P{index:03d}-{candidate_id}-content.json'
                filled, trial = try_candidate(
                    library, entries[candidate_id], data, page, content_path, trial_path, page_out,
                    allow_draft=allow_draft, body_header_pilot=body_enabled, metadata=metadata)
                if 'detail' in trial:
                    trial['reason'] = safe_message(trial.pop('detail'))
                    for partial in (page_out, page_out.with_suffix('.qa.json'), page_out.with_suffix('.colors.json')):
                        partial.unlink(missing_ok=True)
                material_view = page.get('material_matching_content')
                verify_copy = inferred or material_view or (repeat_search and candidate_id != previous_id)
                if filled is not None and verify_copy:
                    copy = material_view or content
                    required = {k:v for k,v in copy.items() if k not in ('item_count','source_refs')}
                    if not retains_text(page_out, text_fields(required)):
                        trial.update(status='rejected', reason_code='SOURCE_TEXT_INCOMPLETE')
                        for partial in (page_out, page_out.with_suffix('.qa.json'), page_out.with_suffix('.colors.json')):
                            partial.unlink(missing_ok=True)
                        filled = None
                    else:
                        trial['editable_copy_verified'] = True
                choice['trial_results'].append(trial)
                if filled is not None:
                    if filled.get('body_header'):
                        choice['body_header'] = filled['body_header']
                    choice['layout_id'] = candidate_id
                    choice['selection_label'] = selection_label(entries[candidate_id])
                    choice.pop('atomic_variant', None)
                    choice.update(atomic_body.trace(entries[candidate_id]))
                    if page.get('role') == 'section' and locked_section_layout_id is None:
                        locked_section_layout_id = candidate_id
                    break
            if filled is None:
                if page.get('role') in STRUCTURAL:
                    raise ValueError(f'第 {index} 页结构模板试填均失败：{choice["trial_results"]}')
                assessment = content.get('layout_assessment') if isinstance(content.get('layout_assessment'), dict) else {}
                use_free = assessment.get('skill_suitable') is False and isinstance(content.get('free_layout'), dict)
                if use_free and not str(assessment.get('reason', '')).strip():
                    raise ValueError(f'第 {index} 页自由编排缺少技能排版不适用的原因')
                choice['selection_mode'] = 'free_composition' if use_free else 'guided_composition'
                choice['selection_label'] = '自由编排' if use_free else '技能排版'
                choice['reason_code'] = 'NO_FIT_AFTER_TRIAL'
                choice['layout_id'] = None
                choice.pop('atomic_variant', None)
            else:
                stamp = filled['source_stamp']
                if not stamp:
                    raise RuntimeError(f'第 {index} 页来源标记缺失')
                choice['source_stamp'] = stamp
        if choice['selection_mode'] == 'guided_composition':
            if page_out.exists():
                raise RuntimeError('试填失败后遗留单页文件，拒绝覆盖')
            try:
                guided = (atomic_body.fallback_content(content, page.get('title'))
                          if choice.get('atomic_input') else dict(content))
                if not guided.get('title'):
                    guided['title'] = page.get('title') or page['purpose']
                guided['type'] = fallback_type(guided)
                guided['_deck_page_number'] = index
                if guided['type'] in STRUCTURAL:
                    raise ValueError('结构页不得由离线正文绘制器替代')
                if guided['type'] == 'cards' and guided.get('variant', 'auto') == 'auto':
                    count = len(guided.get('items', []))
                    if count == 3:
                        guided['variant'] = 'columns'
                    elif count == 6:
                        guided['variant'] = 'stat_rows' if not used_guided_variants.get(('cards', 'stat_rows')) else 'grid'
                if guided['type'] == content.get('type') == 'cards':
                    unused = unmapped_title_body_fields(content)
                    if unused:
                        raise ValueError(f'卡片托底无法承载全部字段：{", ".join(unused)}')
                validate_page(guided, index)
            except ValueError as exc:
                choice['trial_results'].append({'status': 'skill_layout_rejected', 'reason': safe_message(exc)})
                if trial_alternative(page, choice, None, page_out, report['theme'], repeat=False):
                    stamp = None
                elif isinstance(content.get('free_layout'), dict):
                    choice['selection_mode'] = 'free_composition'
                    choice['selection_label'] = '自由编排'
                    choice['reason_code'] = 'SKILL_LAYOUT_VALIDATION_FAILED'
                else:
                    raise ValueError(f'第 {index} 页技能排版不适用，且未提供 free_layout：{exc}') from exc
            if choice['selection_mode'] == 'guided_composition' and not page_out.exists():
                render_guided_page({'theme': report['theme'], 'complete_deck': False,
                                    'pages': [guided]}, page_out)
                stamp = None
                if inferred:
                    if not retains_text(page_out, text_fields(content)):
                        raise ValueError('关系排版未保留完整原文')
                    choice['reason_code'] = 'INFERRED_RELATION_FIT'
                choice['fallback_layout_id'] = guided['type']
                choice['variant'] = resolved_variant(guided, guided['type']) or None
                choice['trial_results'].append({'status': 'guided_drawn', 'library_used': False,
                                                'fallback_layout_id': guided['type'],
                                                'variant': choice['variant']})
        if choice['selection_mode'] == 'free_composition':
            if page.get('role') in STRUCTURAL:
                raise ValueError('结构页不得自由编排')
            free = dict(content)
            free['title'] = free.get('title') or page.get('title', page['purpose'])
            free['type'] = 'free_composition'
            free['_deck_page_number'] = index
            render_guided_page({'theme': report['theme'], 'complete_deck': False,
                                'pages': [free]}, page_out)
            stamp = None
            choice['fallback_layout_id'] = None
            choice['variant'] = None
            choice['trial_results'].append({'status': 'free_drawn', 'library_used': False,
                                            'rationale': free['free_layout']['rationale']})
        if choice['selection_mode'] == 'source_template':
            stamp = choice['source_stamp']
        current = layout_key(choice) if page.get('role') not in STRUCTURAL else None
        if current and actual_layouts and actual_layouts[-1] == current:
            choice['repeated_layout_review'] = True
            if trial_alternative(page, choice, current, page_out, report['theme'], repeat=True):
                stamp = None
            else:
                if page.get('material_excerpt') or (not page.get('layout_id') and content.get('variant', 'auto') == 'auto'):
                    raise ValueError(f'第 {index} 页与上一张正文版式相同，其他排法无法完整保留内容')
                choice['repeat_retained_reason'] = '请求已明确指定版式'
        if choice['selection_mode'] == 'guided_composition':
            final_variant = (choice['fallback_layout_id'], choice.get('variant'))
            used_guided_variants[final_variant] = used_guided_variants.get(final_variant, 0) + 1
        actual_layouts.append(layout_key(choice) if page.get('role') not in STRUCTURAL else None)
        if page.get('material_excerpt'):
            from pptx import Presentation
            source_page = Presentation(page_out)
            notes = source_page.slides[0].notes_slide.notes_text_frame
            if notes is not None:
                notes.text = 'Word 原文｜' + '／'.join(page.get('source_refs', [])) + '\n' + page['material_excerpt']
                source_page.save(page_out)
        slides.append({'path': str(page_out), 'role': page.get('role', 'body'),
                       'layout_id': choice.get('layout_id'), 'source_stamp': stamp})
        free_images = [element['source_path'] for element in content.get('free_layout', {}).get('elements', [])
                       if isinstance(element, dict) and element.get('kind') == 'image' and element.get('source_path')] \
            if isinstance(content.get('free_layout'), dict) else []
        audit_pages.append({'role': page.get('role', 'body'), 'layout_id': choice.get('layout_id'),
                            'directory_item_count': directory_item_count(page)
                            if page.get('role') == 'directory' else None,
                            'selection_mode': choice['selection_mode'], 'selection_label': choice['selection_label'],
                            'source_stamp': stamp,
                            **({'atomic_variant': choice['atomic_variant']} if choice.get('atomic_variant') else {}),
                            **({'body_header': choice['body_header']} if choice.get('body_header') else {}),
                            'data_source': page.get('data_source') or content.get('data_source'),
                            'image_sources': page.get('image_sources') or free_images or ([content['image_path']] if content.get('image_path') else None)})
    assembly = {'theme': report['theme'], 'library_commit': report['library_commit'],
                'library_source': report['library_source'], 'complete_deck': True,
                'font_profile': report['font_profile']['profile']['id'],
                'require_template_source': all(x['selection_mode'] == 'source_template' for x in plan['pages']),
                'slides': slides, 'pages': audit_pages}
    manifest_path = work / 'assembly-plan.json'
    prefilled = check_prefilled(assembly, Path(report['library_path']))
    (work / 'pre-assembly-gate.json').write_text(
        json.dumps(prefilled, ensure_ascii=False, indent=2), encoding='utf-8')
    manifest_path.write_text(json.dumps(assembly, ensure_ascii=False, indent=2), encoding='utf-8')
    render_dir = work / 'rendered'
    native_render = None
    if report.get('assembly_backend') in ('native', 'native_experimental'):
        from native_deck_backend import assemble_and_check
        native = assemble_and_check(assembly, manifest_path, output, prefilled, render_dir)
        finished = native['finished']
        native_render = native['render']
    else:
        report['office_smoke_test'] = {}
        native_render = assemble_office(manifest_path, output, render_dir, sys.executable,
                                        report['font_profile']['profile']['id'], timeout=office_timeout,
                                        smoke_directory=work / 'office-smoke',
                                        smoke_result=report['office_smoke_test'])
        finished = check_finished(output, assembly, prefilled)
    (work / 'final-gate.json').write_text(
        json.dumps(finished, ensure_ascii=False, indent=2), encoding='utf-8')
    audit = audit_deck(manifest_path, output)
    audit_path = work / 'deck-audit.json'
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    if not audit['p0_passed']:
        raise RuntimeError('成稿来源或内容验收失败：' + str(audit['issues'][:5]))
    plan['selection_summary'] = summarize_selection(plan['pages'])
    delivery = assess_delivery(output, render_dir, len(slides), native_render)
    return {'output': str(output.resolve()), 'slides': len(slides),
            'library_used': plan['selection_summary']['知识库模板'] > 0,
            'bundled_body_pages': plan['selection_summary'].get('技能内置组件', 0),
            'source_template_pages': sum(x['selection_mode'] == 'source_template' for x in plan['pages']),
            'guided_pages': sum(x['selection_mode'] == 'guided_composition' for x in plan['pages']),
            'free_pages': sum(x['selection_mode'] == 'free_composition' for x in plan['pages']),
            'selection_summary': plan['selection_summary'],
            'manifest': str(manifest_path), 'audit': str(audit_path), 'render_directory': str(render_dir),
            'pre_assembly_gate': str(work / 'pre-assembly-gate.json'),
            'final_gate': str(work / 'final-gate.json'),
            'assembly_status': 'passed', 'static_audit_status': 'passed',
            'render_evidence': native_render, **delivery}



def main():
    if '--doctor' in sys.argv[1:]:
        from doctor import main as doctor_main
        return doctor_main([arg for arg in sys.argv[1:] if arg != '--doctor'])
    ap = argparse.ArgumentParser(description='知识库预检与逐页规划的统一入口')
    inputs = ap.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--request', type=Path)
    inputs.add_argument('--material', type=Path, help='直接从原始 Word 检索、起草和出稿')
    ap.add_argument('--theme', choices=STYLES, help='Word 出稿主题，默认蓝色')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--plan-out', type=Path)
    output_stage = ap.add_mutually_exclusive_group()
    output_stage.add_argument('--execute-out', type=Path, help='所有页面均有 content 时填充并组装完整 PPTX')
    output_stage.add_argument('--cover-gallery-out', type=Path, help='输出出稿前的带编号封面候选缩略图 PNG')
    ap.add_argument('--library', type=Path, help='测试或固定版本时指定已下载知识库')
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--assembly-backend', choices=BACKENDS, default='auto',
                    help='auto: Windows 使用 PowerPoint，macOS/Linux 使用原生组装；可显式选择')
    ap.add_argument('--native-experimental', action='store_true',
                    help='兼容旧参数，等价于 --assembly-backend native')
    args = ap.parse_args()
    try:
        select_backend(args.assembly_backend, legacy_native=args.native_experimental)
    except ValueError as exc:
        ap.error(str(exc))
    outputs = [path for path in (args.out, args.plan_out, args.execute_out, args.cover_gallery_out)
               if path is not None]
    if any(path.exists() for path in outputs):
        ap.error('输出文件已存在')
    if len(set(path.resolve() for path in outputs)) != len(outputs):
        ap.error('各输出须使用不同文件')
    if args.cover_gallery_out and args.cover_gallery_out.suffix.lower() != '.png':
        ap.error('封面缩略图输出须为 PNG 文件')
    if args.theme and args.request:
        ap.error('逐页请求使用文件中声明的主题')
    request = ({'theme': args.theme or 'blue'} if args.material
               else json.loads(args.request.read_text(encoding='utf-8-sig')))
    report = preflight(request, library=args.library, offline=args.offline,
                       native_experimental=args.native_experimental,
                       assembly_backend=args.assembly_backend)
    if args.material and report['status'] == 'ready':
        from material_first import build
        root = Path(report['library_path'])
        try:
            request, trace = build(args.material, root, load_catalog(root), report['theme'])
        except (OSError, ValueError) as exc:
            ap.error(str(exc))
        report['material_retrieval'] = trace
        report['material_request'] = request
    from structure_content import prepare
    request, content_preparation = prepare(request, auto=True)
    report['content_preparation'] = content_preparation
    if content_preparation['tasks']:
        report['warnings'].append('部分正文保留原有内容结构，整理原因见 content_preparation.tasks。')
    default_profile = {'Windows': 'windows', 'Darwin': 'macos', 'Linux': 'linux'}.get(
        platform.system(), 'linux')
    try:
        font_check = probe_font_profile(request.get('font_profile') or default_profile)
    except ValueError as exc:
        report['status'] = 'blocked'
        report['error_code'] = 'FONT_PROFILE_UNKNOWN'
        report['can_make_complete_deck'] = False
        report['delivery_status'] = 'blocked'
        report['warnings'].append(safe_message(exc))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'status': 'blocked', 'error_code': 'FONT_PROFILE_UNKNOWN',
                          'report': str(args.out)}, ensure_ascii=False))
        return 2
    report['font_profile'] = font_check
    report['delivery_status'] = 'not_started'
    report['deliverable'] = False
    if args.execute_out and font_check['status'] != 'available':
        report['status'] = 'blocked'
        report['error_code'] = font_check['error_code']
        report['can_make_complete_deck'] = False
        report['delivery_status'] = 'blocked'
        report['warnings'].append('任务字体缺失：' + ', '.join(font_check['missing']))
    needs_plan = bool((args.plan_out or args.execute_out) and request.get('pages'))
    if report['status'] == 'ready' and (needs_plan or args.cover_gallery_out):
        stage = 'planning'
        try:
            _load_workflow()
            plan_request = dict(request)
            plan_request['allow_draft'] = request.get('asset_policy', 'verified_draft') != 'approved_only'
            plan_request['allow_provisional'] = request.get('asset_policy') == 'provisional_manual'
            library = Path(report['library_path'])
            catalog = load_catalog(library)
            if args.cover_gallery_out:
                report['cover_gallery'] = preview_covers(
                    library, plan_request, catalog, args.cover_gallery_out,
                    theme=report['theme'], style_family=report['style_family'])
            if needs_plan:
                plan = resolve(library, plan_request, catalog=catalog)
                plan['library_commit'] = report['library_commit']
                plan['library_source'] = report['library_source']
                plan['complete_deck'] = request.get('complete_deck', True)
            if needs_plan and args.execute_out:
                stage = 'execution'
                previous_profile = os.environ.get('EPOINT_FONT_PROFILE')
                os.environ['EPOINT_FONT_PROFILE'] = font_check['profile']['id']
                try:
                    report['execution'] = execute_plan(request, plan, report, args.execute_out, catalog=catalog)
                finally:
                    if previous_profile is None:
                        os.environ.pop('EPOINT_FONT_PROFILE', None)
                    else:
                        os.environ['EPOINT_FONT_PROFILE'] = previous_profile
                report['library_used'] = report['execution']['library_used']
                report['delivery_status'] = report['execution']['delivery_status']
                report['deliverable'] = report['execution']['deliverable']
                report['status'] = 'candidate_created'
                if report['execution'].get('render_error_code'):
                    report['warnings'].append('候选 PPTX 已生成并通过静态审计；渲染待处理：'
                                              + report['execution']['render_error_code'])
            if needs_plan:
                report['selection_summary'] = plan['selection_summary']
            if needs_plan and args.plan_out:
                args.plan_out.parent.mkdir(parents=True, exist_ok=True)
                args.plan_out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
                report['plan_path'] = str(args.plan_out.resolve())
        except (ValueError, KeyError, FileNotFoundError, RuntimeError, OSError, ImportError) as exc:
            report['status'] = 'blocked'
            report['can_make_complete_deck'] = False
            report['delivery_status'] = 'blocked'
            gate_error = str(exc).split(':', 1)[0]
            gate_codes = {'COMPLETE_DECK_PAGES_MISSING', 'COMPLETE_DECK_STRUCTURE_MISSING',
                          'COMPLETE_DECK_STRUCTURE_ORDER', 'STRUCTURE_SOURCE_REQUIRED',
                          'SECTION_LAYOUT_MIXED', 'DIRECTORY_SECTION_COUNT_MISMATCH',
                          'SOURCE_STAMP_NOT_CATALOG_BOUND',
                          'SOURCE_FILE_HASH_MISMATCH', 'RELATION_TARGET_MISSING',
                          'FINISHED_SOURCE_ASSOCIATION_MISMATCH'}
            report['error_code'] = (gate_error if gate_error in gate_codes or gate_error.startswith(('OFFICE_', 'POWERPOINT_', 'RENDER_'))
                                    else 'RUNTIME_DEPENDENCY_MISSING' if isinstance(exc, ImportError)
                                    else 'PAGE_LAYOUT_UNAVAILABLE' if stage == 'planning'
                                    else 'PPTX_EXECUTION_FAILED')
            report['warnings'].append(safe_message(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'error_code': report['error_code'],
                      'library_source': report['library_source'], 'report': str(args.out),
                      'delivery_status': report['delivery_status'], 'deliverable': report.get('deliverable', False)}, ensure_ascii=False))
    return delivery_exit_code(report, executing=bool(args.execute_out))


if __name__ == '__main__':
    raise SystemExit(main())
