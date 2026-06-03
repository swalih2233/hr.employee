from django import template

from common.utils import get_half_day_info

register = template.Library()


@register.filter
def leave_amount(value):
    """
    Format leave counts: 17.0 -> 17, 0.5 -> 0.5, 0.0 -> 0
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
