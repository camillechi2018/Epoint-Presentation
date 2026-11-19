"""Text capacity units shared by selection, preflight and filling."""
import unicodedata


def visual_width_units(text):
    return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in text)


def directory_text_over_capacity(value, limits):
    lines = value.split('\n')
    return (len(value) > limits.get('max_chars', 9999)
            or len(lines) > limits.get('max_lines', 9999)
            or any(visual_width_units(line) > limits.get('max_width_units', 9999) for line in lines))
