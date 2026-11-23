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
