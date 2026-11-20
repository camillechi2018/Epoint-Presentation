"""Try one planned library component using the same rules in delivery and diagnostics."""
import json

from capacity_preflight import missing_binding_paths, preflight
from content_adapters import (
    adapt_for_layout,
    adapt_structural_fields,
    classify_trial_failure,
    field_source_evidence,
    structural_mapping_issue,
)
from fill_layout import fill


def try_candidate(library, entry, data, page, content_path, trial_path, output,
                  *, allow_draft, body_header_pilot, diagnostics=False):
    layout_id = entry["id"]
    title = page.get("title")
    theme = data["theme"]
    candidate, adapter = adapt_for_layout(layout_id, data, title, entry=entry)
    record = {"layout_id": layout_id, "status": "rejected", "content_adapter": adapter}

    if not adapter and entry.get("matching_activation") in ("structure_ready", "pilot_verified"):
        issue = structural_mapping_issue(entry, data, title)
        if issue:
            record.update(reason_code=issue["reason_code"], unmapped_semantic_paths=issue["paths"])
            if diagnostics:
                record["partial_capacity_hard_issues"] = []
                if entry["matching_activation"] == "structure_ready":
                    partial, _, _ = adapt_structural_fields(entry, data, title, diagnostics=True)
                    if isinstance(partial.get("texts"), dict) and partial["texts"]:
                        capacity = preflight(library, entry, partial, title, theme,
                                             body_header_pilot=body_header_pilot)
                        record["partial_capacity_hard_issues"] = capacity["hard_issues"]
            else:
                record["reason"] = "结构字段未完成真实内容映射"
            return None, record

    capacity = preflight(library, entry, data, title, theme, body_header_pilot=body_header_pilot)
    record["capacity_preflight"] = capacity
    if capacity["hard_issues"]:
        record["reason_code"] = "TEXT_OVER_CAPACITY"
        if not diagnostics:
            record["reason"] = "绑定字段容量预检未通过"
        return None, record

    wrap = capacity["wrap_suggestions"]
    if wrap and isinstance(candidate.get("texts"), dict):
        candidate = dict(candidate, texts=dict(candidate["texts"], **wrap))
    if adapter or wrap:
        trial_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=None if diagnostics else 2),
                              encoding="utf-8")
        content_path = trial_path
    options = {"allow_draft": allow_draft, "catalog_entry": entry}
    if "body_header_title" in capacity:
        options["body_header_title"] = capacity["body_header_title"]
    try:
        filled = fill(library, layout_id, content_path, output, **options)
    except (ValueError, KeyError, FileNotFoundError) as exc:
        code = classify_trial_failure(str(exc))
        record.update(reason_code=code, wrap_applied=wrap, detail=str(exc))
        if diagnostics and code == "MISSING_REQUIRED_FIELD":
            fields = json.loads((library / capacity["binding_path"]).read_text(encoding="utf-8-sig"))["fields"]
            record["unmapped_semantic_paths"] = sorted(set(missing_binding_paths(fields, candidate)))
        return None, record

    record.update(status="filled", visual_qa="not_run", wrap_applied=wrap,
                  field_source_evidence=field_source_evidence(
                      dict(data, source_refs=page.get("source_refs", [])), candidate) if adapter else {})
    if diagnostics and filled.get("body_header"):
        record["body_header"] = filled["body_header"]
    return filled, record
