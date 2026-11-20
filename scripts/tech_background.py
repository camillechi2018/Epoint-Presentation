"""Reuse the technology frame's master background and its embedded images."""
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from pptx.parts.image import ImagePart


SKILL = Path(__file__).resolve().parents[1]
EMBED = qn("r:embed")


def background_element(master):
    return master._element.cSld.find(qn("p:bg"))


def background_signature(master, *, ignore_fallback=False):
    background = background_element(master)
    if background is None:
        return ()
    signature = []
    for element in background.iter():
        attrs = dict(element.attrib)
        if ignore_fallback and element.tag == qn("a:blip"):
            attrs.pop(EMBED, None)
        elif EMBED in attrs:
            part = master.part.related_part(attrs[EMBED])
            attrs[EMBED] = sha256(part.blob).hexdigest()
        signature.append((element.tag, tuple(sorted(attrs.items()))))
    return tuple(signature)


@lru_cache(maxsize=4)
def frame_master(asset):
    return Presentation(asset).slides[0].slide_layout.slide_master


def copy_master_background(source, target):
    background = background_element(source)
    if background is None or not any(node.get(EMBED) for node in background.iter()):
        raise ValueError("科技风公共背景缺少内嵌图片")
    if background_signature(target) == background_signature(source):
        return
    replacement = deepcopy(background)
    package = target.part.package
    for element in replacement.iter():
        relation = element.get(EMBED)
        if relation is None:
            continue
        original = source.part.related_part(relation)
        image = next((part for part in package.iter_parts()
                      if part.content_type == original.content_type and part.blob == original.blob), None)
        if image is None:
            image = ImagePart(package.next_image_partname(original.partname.ext),
                              original.content_type, package, original.blob)
        element.set(EMBED, target.part.relate_to(image, RT.IMAGE))
    current = background_element(target)
    if current is not None:
        target._element.cSld.remove(current)
    target._element.cSld.insert(0, replacement)


def shared_master(layout):
    return frame_master(str(SKILL / layout["tech_content_header"]["asset"]))


def shared_background_media(layout):
    master = shared_master(layout)
    parts = (master.part.related_part(node.get(EMBED))
             for node in background_element(master).iter() if node.get(EMBED))
    return {(part.partname.ext, part.blob) for part in parts}


def apply_tech_background(slide, layout):
    copy_master_background(shared_master(layout), slide.slide_layout.slide_master)


def restore_tech_background_fallback(slide, layout):
    master = slide.slide_layout.slide_master
    background = background_element(master)
    if background is None:
        return False
    blip = background.find(".//" + qn("a:blip"))
    if blip is None or blip.get(EMBED):
        return False
    source = shared_master(layout)
    if background_signature(master) != background_signature(source, ignore_fallback=True):
        return False
    copy_master_background(source, master)
    return True


def uses_shared_tech_background(slide, layout):
    signature = background_signature(shared_master(layout))
    return (bool(signature) and slide._element.cSld.find(qn("p:bg")) is None
            and slide.slide_layout._element.cSld.find(qn("p:bg")) is None
            and background_signature(slide.slide_layout.slide_master) == signature)
