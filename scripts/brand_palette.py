"""Keep the Skill's offline RGB roles tied to the existing source templates."""
import json
import re
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

SKILL = Path(__file__).resolve().parents[1]
PROFILE = SKILL / "assets/brand/brand-baseline.json"
LOCK = SKILL / "assets/brand/brand-palette-lock.json"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
HEX = re.compile(r"[0-9A-F]{6}")


def locked_colors(theme):
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    if lock.get("status") != "template_derived_locked":
        raise ValueError("品牌配色锁状态无效")
    if set(profile["themes"]) != set(lock["themes"]):
        raise ValueError("品牌主题与配色锁不一致")
    if theme not in profile["themes"]:
        raise ValueError("未登记的品牌主题：" + theme)
    selected = profile["themes"][theme]
    registered = lock["themes"][theme]
    roles = {key: value for key, value in selected.items()
             if key not in ("source", "logo_appearance", "neutral")}
    if selected["source"] != Path(registered["theme_json"]).name:
        raise ValueError("品牌主题未绑定登记的来源主题文件：" + theme)
    if roles != registered["roles"] or selected["neutral"] != registered["neutral"]:
        raise ValueError("品牌配色与模板配色锁不一致：" + theme)
    values = list(roles.values()) + list(selected["neutral"].values())
    if any(not isinstance(value, str) or not HEX.fullmatch(value) for value in values):
        raise ValueError("品牌配色包含非法 RGB：" + theme)
    return set(values)


def source_xml_colors(path):
    colors = set()
    with ZipFile(path) as package:
        for name in package.namelist():
            if not name.startswith("ppt/") or not name.endswith(".xml"):
                continue
            root = etree.fromstring(package.read(name))
            for element in root.iter():
                if element.tag == f"{{{A}}}srgbClr":
                    value = element.get("val")
                elif element.tag == f"{{{A}}}sysClr":
                    value = element.get("lastClr") or element.get("val")
                else:
                    continue
                if value and HEX.fullmatch(value.upper()):
                    colors.add(value.upper())
    return colors
