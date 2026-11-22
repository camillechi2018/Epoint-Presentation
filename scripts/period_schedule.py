"""Place grouped, editable task bars against source month or quarter axes."""
from pptx.util import Pt

from progress_rings import progress_percentage

LIMITS = {'month': 12, 'quarter': 4}
QUARTERS = ('第一季度', '第二季度', '第三季度', '第四季度')


def schedule_intervals(schedule, items):
    unit = schedule['unit']
    count = LIMITS[unit]
    rows = schedule['rows']
    if not isinstance(items, list) or len(items) != 1 + max(row['item'] for row in rows):
        raise ValueError('PERIOD_SCHEDULE_ITEM_COUNT: 项目或分组数须与原生结构一致')
    intervals = []
    for row_number, row in enumerate(rows, 1):
        item = items[row['item']]
        task = row['task']
        if task is not None:
            tasks = item.get('tasks') if isinstance(item, dict) else None
            expected = sum(other['item'] == row['item'] for other in rows)
            if not isinstance(tasks, list) or len(tasks) != expected:
                raise ValueError(f'PERIOD_SCHEDULE_TASK_COUNT: 第 {row["item"]+1} 组的任务数须与原生结构一致')
            item = tasks[task]
        stages = item.get('stages') if isinstance(item, dict) else None
        if not isinstance(stages, list) or len(stages) != len(row['stages']):
            raise ValueError(f'PERIOD_SCHEDULE_STAGE_COUNT: 第 {row_number} 行的阶段数须与原生结构一致')
        last_end = 0
        for stage_number, (config, stage) in enumerate(zip(row['stages'], stages, strict=True), 1):
            start = stage.get(f'start_{unit}') if isinstance(stage, dict) else None
            end = stage.get(f'end_{unit}') if isinstance(stage, dict) else None
            if type(start) is not int or type(end) is not int or not 1 <= start <= end <= count:
                raise ValueError(f'PERIOD_SCHEDULE_RANGE: 第 {row_number} 行第 {stage_number} 段的起止须为 1–{count} 的有序整数')
            if start <= last_end:
                raise ValueError(f'PERIOD_SCHEDULE_OVERLAP: 第 {row_number} 行第 {stage_number} 段与前段重叠或顺序颠倒')
            rate = progress_percentage(stage.get('value')) if 'progress_id' in config else None
            intervals.append((row_number, stage_number, config, start, end, rate))
            last_end = end
    return intervals


def axis_edges(shapes, schedule):
    unit = schedule['unit']
    if 'header_ids' in schedule:
        headers = [shapes[sid] for sid in schedule['header_ids']]
        labels = [f'{i}月' for i in range(1,13)] if unit == 'month' else list(QUARTERS)
        if [header.text for header in headers] != labels:
            raise ValueError('PERIOD_SCHEDULE_AXIS_LABELS: 原生时间轴标签不符')
        edges = [(header.left, header.left+header.width) for header in headers]
    else:
        ticks = [shapes[sid].left for sid in schedule['boundary_ids']]
        end = shapes[schedule['right_edge_id']]
        edges = list(zip(ticks,[*ticks[1:],end.left+end.width],strict=True))
    if (len(edges) != LIMITS[unit] or any(left >= right for left,right in edges)
            or any(a[1] > b[0] for a,b in zip(edges,edges[1:]))):
        raise ValueError('PERIOD_SCHEDULE_AXIS_GEOMETRY: 原生时间轴刻度有重叠或缺失')
    return edges


def place_progress_row(shapes, config, left, right, percent, axis_left, axis_right):
    track, progress, marker, label, note, lane = (
        shapes[config[key]] for key in ('bar_id','progress_id','marker_id','rate_id','label_id','lane_id'))
    if progress_percentage(label.text) != percent:
        raise ValueError('PERIOD_SCHEDULE_RATE_MISMATCH: 标注百分比须与任务进度一致')
    center_y = lane.top + Pt(10.5)
    tip = left + round((right-left)*percent/100)
    for line,length in ((track,right-left),(progress,tip-left)):
        line.left, line.width, line.top, line.height = left, length, center_y, 0
    if percent == 0:
        progress.line.fill.background()
    marker.width, marker.height = Pt(16), Pt(16)
    marker.left, marker.top = tip-Pt(8), center_y-Pt(8)
    label.left = tip+Pt(9) if tip+Pt(9)+label.width <= axis_right else tip-Pt(9)-label.width
    label.top = lane.top+Pt(1)
    label.text_frame.word_wrap = False
    note.left, note.top, note.width = axis_left, lane.top+Pt(18), axis_right-axis_left
    if icon_id := config.get('note_icon_id'):
        icon = shapes[icon_id]
        icon.width, icon.height = Pt(10), Pt(10)
        icon.left, icon.top = axis_left+Pt(4), lane.top+Pt(22)
        note.left += Pt(13)
        note.width -= Pt(13)
    note.text_frame.word_wrap = False
    return {'percent':percent,'progress_tip_emu':tip,'progress_width_emu':progress.width}


def place_period_bars(slide, schedule, intervals):
    shapes = {shape.shape_id:shape for shape in slide.shapes}
    edges = axis_edges(shapes, schedule)
    results = []
    for row,stage,config,start,end,rate in intervals:
        left, right = edges[start-1][0], edges[end-1][1]
        bar, label = shapes[config['bar_id']], shapes[config['label_id']]
        result = {'row':row,'stage':stage,'shape_id':bar.shape_id,'start':start,'end':end,
                  'left_emu':left,'width_emu':right-left}
        if rate is not None:
            result.update(place_progress_row(shapes,config,left,right,rate,edges[0][0],edges[-1][1]))
        else:
            bar.left, bar.width = left, right-left
            if bar.shape_id != label.shape_id:
                label.left, label.width = left, right-left
            label.text_frame.word_wrap = False
        results.append(result)
    return {'mode':'period_axis_schedule','unit':schedule['unit'],'geometry_bound_to_periods':True,
            'rows':len(schedule['rows']),'bars':results}
