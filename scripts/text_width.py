"""Text capacity units shared by selection, preflight and filling."""
import unicodedata


def visual_width_units(text):
    return sum(2 if unicodedata.east_asian_width(char) in ("W", "F") else 1 for char in text)


def binding_text_issues(value, limits, *, width_units=None):
    """Return the failed rules in the order used by template filling."""
    issues = []
    char_limit = limits.get('max_chars')
    if isinstance(char_limit, int) and len(value) > char_limit:
        issues.append('max_chars')
    allowed = limits.get('allowed_values')
    if allowed is not None and value not in allowed:
        issues.append('allowed_values')
    line_limit = limits.get('max_lines')
    if isinstance(line_limit, int) and value.count('\n') + 1 > line_limit:
        issues.append('max_lines')
    per_line_limit = limits.get('max_chars_per_line')
    if isinstance(per_line_limit, int) and any(len(line) > per_line_limit for line in value.split('\n')):
        issues.append('max_chars_per_line')
    paragraph_limits = limits.get('paragraph_max_chars')
    if paragraph_limits and any(len(line) > maximum for line, maximum in
                                zip(value.split('\n'), paragraph_limits)):
        issues.append('paragraph_max_chars')
    width_limit = limits.get('max_width_units')
    if isinstance(width_limit, (int, float)):
        if width_units is None:
            width_units = max(visual_width_units(line) for line in value.split('\n'))
        if width_units > width_limit:
            issues.append('max_width_units')
    return issues


def directory_text_over_capacity(value, limits):
    lines = value.split('\n')
    return (len(value) > limits.get('max_chars', 9999)
            or len(lines) > limits.get('max_lines', 9999)
            or any(visual_width_units(line) > limits.get('max_width_units', 9999) for line in lines))
