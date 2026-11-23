"""Lightweight content-shape routing for editable body fallback layouts."""
from __future__ import annotations

import json
from pathlib import Path


RULES = Path(__file__).resolve().parents[1] / "assets" / "layouts" / "fallback-layouts.json"

MINIMAL_BODY_TYPES = {"rule_list", "deadline_process"}
MINIMAL_BODY_VARIANTS = {
    "priority_grid": {"summary_split"},
    "process": {"open_steps"},
    "data_table": {"side_notes", "top_notes"},
    "layered_architecture": {"nested_scope"},
    "comparison_chart": {"range_scale"},
}

# Optional legacy IDs still name the same content contract on older requests.
DRAWN_BODY_LAYOUTS = {
    "content-blue-six-longcopy": ("cards", 6, ("blue", "red")),
    "content-body-cards-two-longcopy": ("cards", 2, ("blue", "red")),
    "content-body-cards-three-longcopy": ("cards", 3, ("blue", "red")),
    "content-body-cards-five-longcopy": ("cards", 5, ("blue", "red")),
    "content-body-cards-three-longcopy-tech": ("cards", 3, ("deep-blue-tech",)),
    "content-body-cards-four-tech": ("cards", 4, ("deep-blue-tech",)),
    "content-body-cards-five-longcopy-tech": ("cards", 5, ("deep-blue-tech",)),
    "content-body-cards-six-longcopy-tech": ("cards", 6, ("deep-blue-tech",)),
    "content-body-report-table": ("report_table", 5, ("blue", "red")),
    "content-body-report-table-tech": ("report_table", 5, ("deep-blue-tech",)),
}


def migrated_body_content(content, layout_id):
    kind, count, _ = DRAWN_BODY_LAYOUTS[layout_id]
    if content.get("type") == kind:
        return content
    fields = content.get("texts")
    if not isinstance(fields, dict) or set(content) - {
            "type", "texts", "tables", "title", "theme", "source_refs", "data_source"}:
        return content
    base = {key: value for key, value in content.items() if key not in {"texts", "tables"}}
    if "page.title" in fields:
        base.setdefault("title", fields["page.title"])
    if kind == "cards" and not content.get("tables"):
        expected = {"page.title"}
        items = []
        for i in range(count):
            aliases = ((f"items[{i}].heading", f"text_{4 * i + 4}"),
                       (f"items[{i}].body", f"text_{4 * i + 5}"))
            expected.update(key for pair in aliases for key in pair)
            title, body = (fields.get(path, fields.get(alias)) for path, alias in aliases)
            if not all(isinstance(value, str) and value.strip() for value in (title, body)):
                return content
            items.append({"title": title, "body": body})
        if not set(fields) - expected:
            return dict(base, type=kind, items=items)
    if kind == "report_table" and not set(fields) - {"page.title"}:
        tables = content.get("tables")
        if isinstance(tables, list) and len(tables) == 1 and isinstance(tables[0], dict):
            rows = tables[0].get("rows")
            if (tables[0].get("shape_id") == 2 and isinstance(rows, list) and len(rows) == count + 1
                    and all(isinstance(row, list) and len(row) == 2 for row in rows)):
                return dict(base, type=kind, columns=rows[0],
                            row_labels=[row[0] for row in rows[1:]], items=[row[1] for row in rows[1:]])
    return content


def report_table_layout(content):
    if content.get("type") != "report_table":
        return content
    if set(content) - {"type", "title", "items", "row_labels", "columns", "theme", "library_commit",
                       "unit_claims", "source_refs", "data_source", "logo", "_deck_page_number"}:
        raise ValueError("条目表格含未映射字段，请将原文依据填入对应条目")
    items, labels, columns = (content.get(key) for key in ("items", "row_labels", "columns"))
    if (not all(isinstance(values, list) for values in (items, labels, columns))
            or not 1 <= len(items) <= 8 or len(items) != len(labels) or len(columns) != 2
            or not all(isinstance(value, str) and value.strip()
                       for value in [*items, *labels, *columns])):
        raise ValueError("条目表格需要两个表头，以及一一对应的条目名称和原文依据")
    return dict(content, type="data_table", variant="report",
                rows=[list(row) for row in zip(labels, items, strict=True)])


def uses_minimal_body_layout(kind, variant):
    return isinstance(kind, str) and (kind in MINIMAL_BODY_TYPES or (
        isinstance(variant, str) and variant in MINIMAL_BODY_VARIANTS.get(kind, ())))


def fallback_type(page: dict) -> str:
    if page.get("type"):
        return page["type"]
    if all(key in page for key in ("target", "actual", "gap_reason")):
        return "target_actual_gap"
    if isinstance(page.get("criteria"), list) and isinstance(page.get("options"), list):
        return "decision_matrix"
    if isinstance(page.get("phases"), list) and isinstance(page.get("lanes"), list):
        return "responsibility_swimlane"
    if isinstance(page.get("actions"), list):
        return "data_table"
    if isinstance(page.get("categories"), list) and isinstance(page.get("series"), list):
        return "comparison_chart"
    if isinstance(page.get("series"), list):
        return "assertion_evidence"
    if isinstance(page.get("lead"), dict) and isinstance(page.get("support"), list):
        return "priority_grid"
    if isinstance(page.get("sections"), list):
        return "evidence_matrix"
    if all(isinstance(page.get(key), dict) for key in ("problem", "solution", "outcome")):
        return "problem_solution_outcome"
    if isinstance(page.get("layers"), list):
        return "layered_architecture"
    if isinstance(page.get("paragraphs"), list) and isinstance(page.get("metric"), dict):
        return "longform_metric"
    if isinstance(page.get("columns"), list) and isinstance(page.get("rows"), list):
        return "data_table"
    if isinstance(page.get("milestones"), list):
        return "milestone_timeline"
    if page.get("image_path") and page.get("case_title"):
        return "image_case"
    return "bullets"


def fallback_catalog() -> dict:
    data = json.loads(RULES.read_text(encoding="utf-8-sig"))
    return {row["id"]: row for row in data["layouts"]}
