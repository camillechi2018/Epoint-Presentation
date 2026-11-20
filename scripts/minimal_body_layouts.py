"""Editable, open body layouts for dense rules, tables and short processes."""
from __future__ import annotations

from dataclasses import dataclass, field
import math

from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

from fallback_rules import MINIMAL_BODY_TYPES
from text_width import visual_width_units


LEFT, RIGHT, TOP, BOTTOM = 0.74, 12.59, 1.60, 6.70


@dataclass
class Body:
    text_boxes: list = field(default_factory=list)
    rules: list = field(default_factory=list)
    panels: list = field(default_factory=list)
    table: tuple | None = None

    def text(self, value, x, y, width, height, size=16, color="text", *, bold=False):
        _check_text(value, width, height, size)
        self.text_boxes.append((value, (x, y, width, height), size, color, bold))

    def rule(self, x, y, right=RIGHT):
        self.rules.append((x, y, right))

    def panel(self, x, y, width, height, fill, *, border=None, name=None, rounding=0.0, black_overlay=0.0):
        self.panels.append(((x, y, width, height), fill, border, name, rounding, black_overlay))

    def band(self, value):
        if value is not None:
            self.panel(LEFT, 6.02, RIGHT - LEFT, .65, "soft")
            self.text(value, LEFT + .18, 6.10, RIGHT - LEFT - .36, .48, 14)

    def draw(self, slide, profile, theme, text_box, rectangle, connector):
        typography = profile["typography"]
        for geometry, fill, border, name, rounding, black_overlay in self.panels:
            target = slide.shapes.add_group_shape() if black_overlay else slide
            corners = {"rounded": rounding > 0, "corner_adjustment": rounding}
            shape = rectangle(target, *geometry, theme[fill], theme[border] if border else None,
                              **corners)
            if black_overlay:
                overlay = rectangle(target, *geometry, theme["neutral"]["black"], **corners)
                alpha = OxmlElement("a:alpha")
                alpha.set("val", str(round(black_overlay * 100000)))
                overlay._element.spPr.solidFill.srgbClr.append(alpha)
            if name:
                (target if black_overlay else shape).name = name
        for x, y, right in self.rules:
            connector(slide, x, y, right, y, theme["border"], .8)
        for value, geometry, size, color, bold in self.text_boxes:
            ink = theme["neutral"]["white"] if color == "white" else theme[color]
            text_box(slide, value, *geometry, size, ink,
                     typography["heading" if bold else "body"], bold=bold, valign=MSO_ANCHOR.TOP)
        if self.table:
            _draw_table(slide, self.table, typography, theme)


def _check_text(value, width, height, size):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("正文或标签必须是非空文本")
    units_per_line = max(1, int(width * 72 / (size * .60)))
    required_lines = sum(max(1, math.ceil(visual_width_units(line) / units_per_line))
                         for line in value.split("\n"))
    available_lines = int(height * 72 / (size * 1.16))
    if required_lines > available_lines:
        raise ValueError(f"正文超出排版容量，请精简或拆页：{value[:24]}")


def _items(data, key, minimum, maximum):
    values = data.get(key)
    if (not isinstance(values, list) or not minimum <= len(values) <= maximum
            or any(not isinstance(item, dict) for item in values)):
        raise ValueError(f"{key} 须包含 {minimum}–{maximum} 个对象")
    return values


def _rows(body, items, *, x, y, width, height, numbered=True, conditions=False, label_width=None):
    row_height = min(1.36, height / len(items))
    if label_width is None:
        label_width = min(width * .30, 2.32)
    condition_width = 1.62 if conditions else 0
    for index, item in enumerate(items):
        row_y = y + index * row_height
        number_width = .48 if numbered else 0
        if numbered:
            body.text(f"{index + 1:02d}", x, row_y + .14, .36, .30, 13, "primary")
        body.text(item.get("title"), x + number_width, row_y + .10, label_width - number_width - .12,
                  row_height - .17, 15, "primary", bold=True)
        left = x + label_width
        body.text(item.get("body"), left, row_y + .10, width - label_width - condition_width - .12,
                  row_height - .17, 15)
        if conditions and "condition" in item:
            body.text(item["condition"], x + width - 1.50, row_y + .12,
                      1.44, row_height - .18, 13, "muted")
        if index < len(items) - 1:
            body.rule(x, row_y + row_height - .04, x + width)


def _rule_list(page, body):
    items = _items(page, "items", 2, 6)
    takeaway = page.get("takeaway")
    _rows(body, items, x=LEFT, y=TOP, width=RIGHT - LEFT,
          height=(5.85 if takeaway is not None else BOTTOM) - TOP,
          conditions=any("condition" in item for item in items))
    body.band(takeaway)


def _split_summary(page, body):
    lead = page.get("lead")
    if not isinstance(lead, dict):
        raise ValueError("双栏摘要需要 lead 对象")
    panel_left = LEFT - .25
    panel_width = 3.5
    panel_padding = .30
    text_left = panel_left + panel_padding
    text_width = panel_width - 2 * panel_padding
    support_left = panel_left + panel_width + .40
    detail_left = 7.58
    body.panel(panel_left, TOP, panel_width, BOTTOM - TOP, "primary",
               name="body:summary-panel", rounding=.04, black_overlay=.20)
    body.text(lead.get("title"), text_left, TOP + .40, text_width, 1.13, 23, "white", bold=True)
    body.text(lead.get("body"), text_left, 3.24, text_width, 2.87, 17, "white")
    _rows(body, _items(page, "support", 2, 5), x=support_left, y=TOP, width=RIGHT - support_left,
          height=BOTTOM - TOP, numbered=False, label_width=detail_left - support_left)


def _deadline_process(page, body):
    deadlines = _items(page, "deadlines", 2, 2)
    for index, item in enumerate(deadlines):
        y = TOP + index * 2.12
        body.text(item.get("label"), LEFT, y, 4.32, .36, 16, "muted", bold=True)
        value, unit = item.get("value"), item.get("unit")
        if (type(value) not in (str, int, float) or not str(value).strip()
                or (isinstance(value, float) and not math.isfinite(value))
                or not isinstance(unit, str) or not unit.strip()):
            raise ValueError("时限需要数值和单位")
        body.text(str(value), LEFT, y + .42, 1.16, .60, 29, "primary", bold=True)
        body.text(unit, LEFT + 1.22, y + .63, 3.08, .35, 14, "muted")
        body.text(item.get("body"), LEFT, y + 1.11, 4.30, .80, 15)
        if index == 0:
            body.rule(LEFT, y + 1.98, 5.04)
    _rows(body, _items(page, "steps", 2, 5), x=5.48, y=TOP, width=RIGHT - 5.48,
          height=4.23, label_width=1.56)
    body.band(page.get("takeaway"))


def _open_steps(page, body):
    items = _items(page, "items", 3, 5)
    gap = .26
    width = (RIGHT - LEFT - gap * (len(items) - 1)) / len(items)
    body.rule(LEFT, 2.44)
    for index, item in enumerate(items):
        x = LEFT + index * (width + gap)
        body.text(f"{index + 1:02d}", x, 1.92, .40, .33, 14, "primary", bold=True)
        if "stage" in item:
            body.text(item["stage"], x + .49, 1.92, width - .52, .35, 13, "muted")
        body.text(item.get("title"), x, 2.60, width, .70, 19, "primary", bold=True)
        body.text(item.get("body"), x, 3.42, width, 1.53 if "output" in item else 2.18, 15)
        if "output" in item:
            body.text(item["output"], x, 5.09, width, .61, 14, "muted", bold=True)
    body.band(page.get("takeaway"))


def _nested_scope(page, body):
    outer, inner = page.get("outer"), page.get("inner")
    if not isinstance(outer, dict) or not isinstance(inner, dict):
        raise ValueError("嵌套层级需要 outer 和 inner 对象")
    children = _items(inner, "children", 2, 3)
    rules = _items(page, "rules", 2, 4)

    body.panel(LEFT, TOP, 5.72, 3.67, "surface", border="border")
    body.text(outer.get("title"), LEFT + .20, TOP + .16, 5.32, .36, 16, "muted", bold=True)
    body.panel(LEFT + .20, 2.25, 5.32, 2.82, "soft", border="border")
    body.text(inner.get("title"), LEFT + .40, 2.45, 4.92, .38, 18, "primary", bold=True)
    body.text(inner.get("body"), LEFT + .40, 2.90, 4.92, .50, 15)
    gap = .12
    width = (4.92 - gap * (len(children) - 1)) / len(children)
    for index, child in enumerate(children):
        x = LEFT + .40 + index * (width + gap)
        body.panel(x, 3.55, width, 1.30, "surface", border="border")
        body.text(child.get("title"), x + .10, 3.68, width - .20, .28, 14, "primary", bold=True)
        body.text(child.get("body"), x + .10, 4.04, width - .20, .68, 13)
    if "note" in page:
        body.text(page["note"], LEFT, 5.44, 5.72, .48, 14, "muted")
    if "principles" in page:
        labels = page["principles"]
        if (not isinstance(labels, list) or not 1 <= len(labels) <= 6
                or any(not isinstance(label, str) or not label.strip() for label in labels)):
            raise ValueError("principles 须包含 1–6 项文本")
        body.text("  ·  ".join(labels), LEFT, 6.06, 5.72, .32, 13, "muted")
    for index, item in enumerate(rules):
        y = TOP + index * 1.24
        body.text(item.get("title"), 6.91, y, 5.62, .35, 16, "primary", bold=True)
        body.text(item.get("body"), 6.91, y + .43, 5.62, .75, 15)
        if index < len(rules) - 1:
            body.rule(6.91, y + 1.20)


def _finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _range_scale(page, body):
    scale = page.get("scale")
    if not isinstance(scale, dict):
        raise ValueError("区间图需要 scale 对象")
    start, end, ticks = scale.get("min"), scale.get("max"), scale.get("ticks")
    if (not _finite_number(start) or not _finite_number(end) or start >= end
            or not _finite_number(end - start)):
        raise ValueError("刻度必须提供有限数值，且最小值小于最大值")
    if (not isinstance(ticks, list) or not 2 <= len(ticks) <= 6
            or any(not _finite_number(tick) for tick in ticks)
            or ticks[0] != start or ticks[-1] != end
            or any(a >= b for a, b in zip(ticks, ticks[1:]))):
        raise ValueError("刻度需要 2–6 个递增的点，包含最小值和最大值")
    rows = _items(page, "ranges", 2, 6)
    highlight = page.get("highlight")
    if highlight is not None and not isinstance(highlight, dict):
        raise ValueError("highlight 须为对象")
    chart_x = LEFT + 1.16
    chart_width = 5.75 if highlight is not None else 8.74
    data_x = chart_x + chart_width + .18

    def position(value):
        return chart_x + chart_width * ((value - start) / (end - start))

    y = 1.75
    for index, item in enumerate(rows):
        low, high = item.get("min"), item.get("max")
        if not _finite_number(low) or not _finite_number(high) or not start <= low <= high <= end:
            raise ValueError(f"第 {index + 1} 行区间上下限无效或超出刻度")
        body.text(item.get("label"), LEFT, y + .02, .98, .32, 15, bold=True)
        body.panel(chart_x, y + .16, chart_width, .075, "border")
        if low == high:
            body.panel(position(low) - .04, y + .10, .08, .20, "primary", name="body:range-point")
            label = str(low)
        else:
            body.panel(position(low), y + .13, position(high) - position(low),
                       .14, "primary", name="body:range-interval")
            label = f"{low} – {high}"
        body.text(label, data_x, y + .03, 1.65, .30, 13, "muted")
        y += .52
    body.rule(chart_x, y + .04, chart_x + chart_width)
    for index, tick in enumerate(ticks):
        x = position(tick)
        if index and x - position(ticks[index - 1]) < .78:
            raise ValueError("刻度标签间距不足，请减少刻度")
        body.panel(x - .006, y + .04, .012, .08, "border")
        body.text(str(tick), x - .30, y + .17, .66, .25, 11, "muted")
    if "caption" in page:
        body.text(page["caption"], LEFT, y + .47, chart_width + 1.16, .27, 12, "muted")
    if highlight is not None:
        value = highlight.get("value")
        if not _finite_number(value):
            raise ValueError("摘要指标需要有限数值")
        body.panel(9.61, TOP, 2.98, 3.87, "soft")
        body.text(highlight.get("label"), 9.81, 1.92, 2.54, .35, 15, "muted", bold=True)
        unit = highlight.get("unit", "")
        if not isinstance(unit, str):
            raise ValueError("摘要指标单位须为文本")
        body.text(f"{value} {unit}".rstrip(), 9.81, 2.49, 2.54, .66, 34, "primary", bold=True)
        body.text(highlight.get("body"), 9.81, 3.48, 2.54, 1.57, 15)
    if "takeaway" in page:
        body.panel(LEFT, 5.86, RIGHT - LEFT, .80, "soft")
        body.text(page["takeaway"], LEFT + .18, 5.93, RIGHT - LEFT - .36, .67, 13)


def _noted_table(page, body):
    side = page["variant"] == "side_notes"
    notes = _items(page, "notes_items", 1, 4 if side else 2)
    if side:
        for index, note in enumerate(notes):
            y = TOP + index * 1.16
            body.text(note.get("title"), 9.22, y, 3.34, .38, 16, "primary", bold=True)
            body.text(note.get("body"), 9.22, y + .39, 3.34, .73, 14)
        width, top = 8.18, TOP
    else:
        note_width = (RIGHT - LEFT - .28 * (len(notes) - 1)) / len(notes)
        for index, note in enumerate(notes):
            x = LEFT + index * (note_width + .28)
            body.text(note.get("title"), x, TOP, note_width, .36, 16, "primary", bold=True)
            body.text(note.get("body"), x, TOP + .40, note_width, .53, 14)
        width, top = RIGHT - LEFT, 2.73
    columns, rows = page.get("columns"), page.get("rows")
    if (not isinstance(columns, list) or not 2 <= len(columns) <= 6
            or any(not isinstance(label, str) or not label.strip() for label in columns)):
        raise ValueError("表格需要 2–6 个非空列标题")
    if (not isinstance(rows, list) or not 1 <= len(rows) <= 6 or any(
            not isinstance(row, list) or len(row) != len(columns)
            or any(type(cell) not in (str, int, float) for cell in row) for row in rows)):
        raise ValueError("表格需要 1–6 行，且每行与列标题等长")
    cells = [columns] + [[str(cell) for cell in row] for row in rows]
    weights = [max(1, min(6, max(visual_width_units(row[i]) for row in cells) / 10))
               for i in range(len(columns))]
    available = width - len(weights) * 1.0
    widths = [1.0 + available * weight / sum(weights) for weight in weights]
    row_height = min(.68, (6.35 - top) / len(cells))
    for row in cells:
        for value, cell_width in zip(row, widths):
            if value:
                _check_text(value, cell_width - .22, row_height - .08, 14)
    body.table = (top, widths, row_height, cells)
    source = page.get("data_source")
    if source is not None:
        body.text(source, LEFT, top + row_height * len(cells) + .08, width, .42, 11, "muted")


def _draw_table(slide, spec, typography, theme):
    top, widths, row_height, cells = spec
    graphic = slide.shapes.add_table(len(cells), len(widths), Inches(LEFT), Inches(top),
                                     Inches(sum(widths)), Inches(len(cells) * row_height))
    graphic.name = "body:editable-table"
    table = graphic.table
    table.first_row = table.horz_banding = False
    for column, width in zip(table.columns, widths):
        column.width = Inches(width)
    for row_index, values in enumerate(cells):
        table.rows[row_index].height = Inches(row_height)
        for column_index, value in enumerate(values):
            cell = table.cell(row_index, column_index)
            cell.fill.solid()
            background = "soft" if row_index == 0 else ("surface" if row_index % 2 else "canvas")
            cell.fill.fore_color.rgb = RGBColor.from_string(theme[background])
            # Use the row fills as separators without inheriting table-style grid lines.
            properties = cell._tc.get_or_add_tcPr()
            for edge in reversed(("lnL", "lnR", "lnT", "lnB")):
                border = OxmlElement("a:" + edge)
                border.append(OxmlElement("a:noFill"))
                properties.insert(0, border)
            cell.margin_left = cell.margin_right = Inches(.11)
            cell.margin_top = cell.margin_bottom = Inches(.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.text = value
            cell.text_frame.word_wrap = True
            for paragraph in cell.text_frame.paragraphs:
                paragraph.space_before = paragraph.space_after = Pt(0)
                paragraph.line_spacing = 1.12
                paragraph.font.size = Pt(14)
                paragraph.font.name = typography["heading" if row_index == 0 else "body"]
                paragraph.font.bold = row_index == 0
                paragraph.font.color.rgb = RGBColor.from_string(theme["text"])


def verify_header_title(title, spec, index):
    _, _, width, height = spec["title_box_inches"]
    try:
        _check_text(title, width, height, spec["title_size_pt"])
    except ValueError as exc:
        raise ValueError(f"第 {index} 页标题超出当前主题的公共页眉容量，请使用更短的页标题") from exc


def compose(page, kind, index):
    body = Body()
    draw = {
        "rule_list": _rule_list,
        "deadline_process": _deadline_process,
        "summary_split": _split_summary,
        "open_steps": _open_steps,
        "side_notes": _noted_table,
        "top_notes": _noted_table,
        "nested_scope": _nested_scope,
        "range_scale": _range_scale,
    }[kind if kind in MINIMAL_BODY_TYPES else page["variant"]]
    try:
        draw(page, body)
    except ValueError as exc:
        raise ValueError(f"第 {index} 页 {exc}") from exc
    return body
