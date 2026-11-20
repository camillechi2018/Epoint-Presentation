"""Translate internal OPC relationships to ZIP member names."""

import posixpath
from urllib.parse import unquote


def rels_name(part):
    folder, name = posixpath.split(part)
    return posixpath.join(folder, "_rels", name + ".rels")


def resolve_target(owner, target):
    """Resolve a package-root or owner-relative target without a leading slash."""
    target = unquote(target)
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    return posixpath.normpath(posixpath.join(posixpath.dirname(owner), target))
