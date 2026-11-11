from django import template

from common.utils import get_half_day_info, can_withdraw_leave

register = template.Library()


@register.filter
def leave_amount(value):
    """
    Format leave counts: 17.0 -> 17, 4.5 -> 4.5, 0.5 -> 0.5, 0.0 -> 0
    """
    if value is None:
        return "0"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if v == int(v):
        return str(int(v))
    return ("%s" % v).rstrip("0").rstrip(".")


@register.filter(name="add_leaves")
def add_leaves(value, arg):
    """
    Safely add two leave values as floats without integer truncation.
    For example: 4.5 + 0 = 4.5 (Django's built-in add converts 4.5 to int 4).
    """
    try:
        v = float(value if value is not None else 0)
        a = float(arg if arg is not None else 0)
        res = v + a
        return int(res) if res == int(res) else res
    except (TypeError, ValueError):
        return value


@register.filter(name="add_float")
def add_float(value, arg):
    return add_leaves(value, arg)


@register.filter(name="add")
def float_safe_add(value, arg):
    """
    Float-safe override of Django's default add filter.
    Prevents float truncation like int(4.5) -> 4 while preserving normal behavior.
    """
    try:
        v = float(value if value is not None else 0)
        a = float(arg if arg is not None else 0)
        res = v + a
        return int(res) if res == int(res) else res
    except (TypeError, ValueError):
        try:
            return value + arg
        except Exception:
            return ""


@register.filter
def leave_type_name(leave):
    """Leave type label (Annual Leave, Medical Leave, etc.)."""
    if hasattr(leave, "get_leave_type_display"):
        label = leave.get_leave_type_display()
        if label:
            return label
    return leave.leave_type or "—"


@register.filter
def leave_days_count(leave):
    """Duration: 0.5 day, 1 day, 2 days."""
    if getattr(leave, "is_half_day", False):
        return "0.5 day"
    duration = float(getattr(leave, "leave_duration", 0) or 0)
    if duration == int(duration):
        n = int(duration)
        return f"{n} day" if n == 1 else f"{n} days"
    return f"{duration} days"


@register.filter
def leave_session_time(leave):
    """Morning/Afternoon time for half-day; em dash for full day."""
    info = get_half_day_info(leave)
    if not info:
        return "—"
    return f"{info['label']} ({info['time']})"


@register.filter
def can_withdraw(leave):
    """True when an approved leave is within the 7-day withdrawal window."""
    return can_withdraw_leave(leave)
