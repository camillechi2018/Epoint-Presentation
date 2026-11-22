"""Bind percentage labels to the sweep of native PowerPoint rings."""
import re

FULL_TURN = 360 * 60000
TOP_ANGLE = 270 * 60000


def progress_percentage(value):
    if isinstance(value, str) and re.fullmatch(r'[0-9]{1,3}%', value.strip()):
        percent = int(value.strip()[:-1])
        if percent <= 100:
            return percent
    raise ValueError('PROGRESS_RING_PERCENTAGE: 进度须为 0–100 的整数百分比')


def apply_progress_rings(shapes, rules, texts, aliases):
    updates = []
    for rule in rules:
        field = rule['value_field']
        percent = progress_percentage(texts.get(aliases.get(field, field)))
        arc_id = rule['arc_shape_id']
        shape = shapes.get(arc_id)
        label = shapes.get(rule['text_shape_id'])
        if label is None or not label.has_text_frame:
            raise ValueError(f"PROGRESS_RING_LABEL_MISSING: {rule['text_shape_id']}")
        geometry = shape._element.spPr.xpath('a:prstGeom[@prst="arc"]') if shape is not None else []
        if len(geometry) != 1:
            raise ValueError(f'PROGRESS_RING_ARC_MISSING: {arc_id}')
        guides = geometry[0].xpath('a:avLst/a:gd')
        if [guide.get('name') for guide in guides] != ['adj1', 'adj2']:
            raise ValueError(f'PROGRESS_RING_ARC_GUIDES: {arc_id}')
        updates.append((shape, label, geometry[0], guides, field, percent))

    result = []
    for shape, label, geometry, guides, field, percent in updates:
        label.text_frame.word_wrap = False
        sweep = FULL_TURN * percent // 100
        if percent == 100:
            geometry.set('prst', 'ellipse')
            for guide in guides:
                guide.getparent().remove(guide)
            shape.fill.background()
        elif percent == 0:
            shape.fill.background()
            shape.line.fill.background()
        else:
            guides[0].set('fmla', f'val {TOP_ANGLE}')
            guides[1].set('fmla', f'val {(TOP_ANGLE + sweep) % FULL_TURN}')
        result.append({'arc_shape_id': shape.shape_id, 'value_field': field,
                       'percent': percent, 'sweep_angle_units': sweep})
    return result
