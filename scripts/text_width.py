"""Text capacity units shared by selection, preflight and filling."""
import unicodedata


def visual_width_units(text):
    return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in text)
