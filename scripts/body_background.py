"""Validate the shared editable background on blue/red body slides."""
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE


def uses_component_atmosphere(layout, layout_id, theme):
    spec = layout["content_atmosphere"]
    return theme in spec["themes"] and layout_id in spec["component_layouts"]


def blue_red_background_issue(shapes, layout, theme_name, palette):
    spec = layout["content_atmosphere"]
    expected = spec["circles_by_theme"].get(theme_name)
    atmosphere = [shape for shape in shapes if shape.name.startswith("brand:atmosphere:")]
    if (expected is None or not shapes or shapes[0].name != "brand:canvas"
            or len(atmosphere) != len(expected)
            or shapes[1:1 + len(atmosphere)] != atmosphere
            or [shape.name for shape in atmosphere] !=
            [f"brand:atmosphere:{i}" for i in range(1, len(atmosphere) + 1)]):
        return "new_drawn_background", "新绘正文画布或弥散层缺失、顺序错误"
    canvas = shapes[0]
    expected_bounds = (0, 0, Inches(layout["canvas"]["width_inches"]), Inches(layout["canvas"]["height_inches"]))
    bounds = (canvas.left, canvas.top, canvas.width, canvas.height)
    if (sum(shape.name == "brand:canvas" for shape in shapes) != 1
            or canvas.shape_type != 1 or canvas.auto_shape_type != MSO_SHAPE.RECTANGLE
            or str(canvas.fill.fore_color.rgb) != palette["canvas"]
            or any(abs(value - target) > 1000 for value, target in zip(bounds, expected_bounds))):
        return "new_drawn_canvas", "正文画布的数量、形状、尺寸、位置或底色不符合公共配置"
    for shape, item in zip(atmosphere, expected):
        alpha = shape._element.xpath("./p:spPr/a:solidFill/a:srgbClr/a:alpha")
        soft_edge = shape._element.xpath("./p:spPr/a:effectLst/a:softEdge")
        bounds = (shape.left, shape.top, shape.width, shape.height)
        if (shape.shape_type != 1 or shape.auto_shape_type != MSO_SHAPE.OVAL
                or str(shape.fill.fore_color.rgb) != palette[item["color_role"]]
                or len(alpha) != 1 or alpha[0].get("val") != str(round(item["opacity"] * 100000))
                or len(soft_edge) != 1 or soft_edge[0].get("rad") != str(Pt(spec["blur_pt"]))
                or any(abs(value - Inches(target)) > 1000
                       for value, target in zip(bounds, item["box_inches"]))):
            return "new_drawn_atmosphere", "新绘正文弥散层颜色、透明度、柔边或位置偏移"
    return None
