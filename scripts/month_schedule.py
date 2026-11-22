"""Validate and position editable native task bars against a fixed month axis."""


def month_ranges(schedule, items):
    rows = schedule['bar_shape_ids_by_row']
    if not isinstance(items, list) or len(items) != len(rows):
        raise ValueError('MONTH_SCHEDULE_ROW_COUNT: 排期项目须与登记的原生行数一致')
    intervals = []
    for row_index, (row, item) in enumerate(zip(rows, items, strict=True), 1):
        stages = item.get('stages') if isinstance(item, dict) else None
        if not isinstance(stages, list) or len(stages) != len(row):
            raise ValueError(f'MONTH_SCHEDULE_STAGE_COUNT: 第 {row_index} 行缺少完整阶段')
        last_end = 0
        for stage_index, (shape_id, stage) in enumerate(zip(row, stages, strict=True), 1):
            start = stage.get('start_month') if isinstance(stage, dict) else None
            end = stage.get('end_month') if isinstance(stage, dict) else None
            if type(start) is not int or type(end) is not int or not 1 <= start <= end <= 12:
                raise ValueError(f'MONTH_SCHEDULE_MONTH_RANGE: 第 {row_index} 行第 {stage_index} 段须填写 1–12 月的有效区间')
            if start <= last_end:
                raise ValueError(f'MONTH_SCHEDULE_OVERLAP: 第 {row_index} 行第 {stage_index} 段与前段重叠或顺序颠倒')
            intervals.append((shape_id, start, end))
            last_end = end
    return intervals


def place_month_bars(slide, schedule, intervals):
    shapes = {shape.shape_id: shape for shape in slide.shapes}
    months = [shapes.get(shape_id) for shape_id in schedule['month_header_shape_ids']]
    if len(months) != 12 or any(month is None or not month.has_text_frame for month in months):
        raise ValueError('MONTH_SCHEDULE_AXIS_MISSING')
    if [month.text for month in months] != [f'{i}月' for i in range(1, 13)]:
        raise ValueError('MONTH_SCHEDULE_AXIS_ORDER')
    if any(a.left + a.width > b.left or a.width <= 0
           for a,b in zip(months, months[1:])) or months[-1].width <= 0:
        raise ValueError('MONTH_SCHEDULE_AXIS_GEOMETRY')

    updates = []
    for shape_id, start, end in intervals:
        shape = shapes.get(shape_id)
        if shape is None or not shape.has_text_frame:
            raise ValueError('MONTH_SCHEDULE_BAR_MISSING')
        left = months[start-1].left
        right = months[end-1].left + months[end-1].width
        updates.append((shape, start, end, left, right-left))
    for bar, _, _, left, width in updates:
        bar.left = left
        bar.width = width
    return {'mode':'month_axis_schedule','rows':len(schedule['bar_shape_ids_by_row']),
            'geometry_bound_to_months':True,
            'bars':[{'shape_id':bar.shape_id,'start_month':start,'end_month':end,
                     'left_emu':int(left),'width_emu':int(width)}
                    for bar,start,end,left,width in updates]}
