from datetime import date, datetime
import logging
import os

from django.conf import settings
from django.db.models import Q
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

EXCEL_RELATIVE_PATH = os.path.join("leave_reports", "approved_leaves.xlsx")

HEADERS = [
    "Name",
    "ID",
    "Designation",
    "Joining Date",
    "Role",
    "Leave Type",
    "Applied Leave Dates",
    "Days",
    "Status",
    "Annual Leave Balance",
    "Sick Leave Balance",
]


def get_approved_leaves_excel_path():
    reports_dir = os.path.join(settings.MEDIA_ROOT, "leave_reports")
    os.makedirs(reports_dir, exist_ok=True)
    return os.path.join(reports_dir, "approved_leaves.xlsx")


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _format_date(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d %b %Y")
    return str(value)


def _leave_type_label(leave_type):
    if leave_type == "AL":
        return "Annual Leave"
    if leave_type == "ML":
        return "Sick Leave"
    return leave_type or ""


def _applied_dates(start_date, end_date, is_half_day=False, half_day_session=None):
    start_text = _format_date(start_date)
    end_text = _format_date(end_date)
    if start_text and end_text and start_text == end_text:
        dates = start_text
    elif start_text and end_text:
        dates = f"{start_text} to {end_text}"
    else:
        dates = start_text or end_text
    if is_half_day:
        session = "Morning" if half_day_session == "AM" else "Afternoon" if half_day_session == "PM" else "Half day"
        dates = f"{dates} ({session})"
    return dates


def _row_from_profile(profile, role, leave):
    user = getattr(profile, "user", None) if profile else None
    name = ""
    if user:
        name = user.get_full_name()
        if not name:
            name = getattr(user, "email", "") or getattr(user, "username", "")
    if not name and profile:
        name = f"{role} #{getattr(profile, 'id', '')}"

    person_id = (getattr(profile, "employe_id", None) or getattr(profile, "manager_id", None) or "") if profile else ""
    joining = _format_date(getattr(profile, "date_of_joining", None)) if profile else ""
    status_label = getattr(leave, "status", None) or "Approved"

    return [
        name,
        person_id,
        (profile.designation if profile else "") or "",
        joining,
        role,
        _leave_type_label(leave.leave_type),
        _applied_dates(
            leave.start_date,
            leave.end_date,
            getattr(leave, "is_half_day", False),
            getattr(leave, "half_day_session", None),
        ),
        leave.leave_duration or 0,
        status_label,
        getattr(profile, "available_leaves", 0) if profile else 0,
        getattr(profile, "available_medical_leaves", 0) if profile else 0,
    ]


def _build_leave_date_filter(filter_date=None, start_date=None, end_date=None):
    parsed_filter = _parse_date(filter_date)
    parsed_start = _parse_date(start_date)
    parsed_end = _parse_date(end_date)

    if parsed_start and parsed_end:
        return Q(start_date__lte=parsed_end, end_date__gte=parsed_start)

    target = parsed_filter or parsed_start or parsed_end
    if target:
        return (
            Q(start_date__lte=target, end_date__gte=target)
            | Q(start_date=target)
            | Q(created_date=target)
        )

    return Q()


def collect_approved_leave_rows(filter_date=None, start_date=None, end_date=None):
    from employe.models import LeaveRequest
    from managers.models import UnifiedLeaveRequest

    date_q = _build_leave_date_filter(
        filter_date=filter_date,
        start_date=start_date,
        end_date=end_date,
    )

    rows = []

    # 1. Employee LeaveRequest (includes current and previous employees)
    employee_leaves_qs = LeaveRequest.objects.filter(
        status="Approved",
        is_withdrawn=False,
    )
    if date_q:
        employee_leaves_qs = employee_leaves_qs.filter(date_q)

    employee_leaves = (
        employee_leaves_qs
        .select_related("employee", "employee__user")
        .order_by("start_date", "id")
    )
    for leave in employee_leaves:
        if leave.employee:
            rows.append(_row_from_profile(leave.employee, "Employee", leave))

    # 2. UnifiedLeaveRequest for employees (if any)
    unified_emp_qs = UnifiedLeaveRequest.objects.filter(
        requested_by_role="employee",
        is_approved=True,
        is_withdrawn=False,
    )
    if date_q:
        unified_emp_qs = unified_emp_qs.filter(date_q)

    for leave in unified_emp_qs.select_related("employee", "employee__user").order_by("start_date", "id"):
        if leave.employee:
            rows.append(_row_from_profile(leave.employee, "Employee", leave))

    # 3. Manager UnifiedLeaveRequest
    manager_leaves_qs = UnifiedLeaveRequest.objects.filter(
        requested_by_role="manager",
        is_approved=True,
        is_withdrawn=False,
    )
    if date_q:
        manager_leaves_qs = manager_leaves_qs.filter(date_q)

    manager_leaves = (
        manager_leaves_qs
        .select_related("manager", "manager__user")
        .order_by("start_date", "id")
    )
    for leave in manager_leaves:
        if leave.manager:
            rows.append(_row_from_profile(leave.manager, "Manager", leave))

    # 4. Old ManagerLeaveRequest (if any exist in database)
    try:
        from managers.models import ManagerLeaveRequest
        old_mgr_qs = ManagerLeaveRequest.objects.filter(is_approved=True)
        if date_q:
            old_mgr_qs = old_mgr_qs.filter(date_q)
        for leave in old_mgr_qs.select_related("manager", "manager__user").order_by("start_date", "id"):
            if leave.manager:
                rows.append(_row_from_profile(leave.manager, "Manager", leave))
    except Exception:
        pass

    return rows


def write_approved_leaves_workbook(path_or_buffer, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Approved Leaves"
    sheet.append(HEADERS)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F2937")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )

    for cell in sheet[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin

    for row in rows:
        sheet.append(row)

    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, max_col=len(HEADERS)):
        for cell in row:
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = thin

    widths = [28, 16, 22, 16, 12, 16, 36, 10, 14, 22, 20]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    sheet.auto_filter.ref = sheet.dimensions
    sheet.freeze_panes = "A2"
    workbook.save(path_or_buffer)
    if hasattr(path_or_buffer, "seek"):
        path_or_buffer.seek(0)
    return path_or_buffer


def sync_approved_leaves_excel(filter_date=None, start_date=None, end_date=None):
    """Rebuild the founder Excel sheet from approved leaves."""
    try:
        path = get_approved_leaves_excel_path()
        rows = collect_approved_leave_rows(
            filter_date=filter_date,
            start_date=start_date,
            end_date=end_date,
        )
        write_approved_leaves_workbook(path, rows)
        return path
    except Exception:
        logger.exception("Failed to update approved leaves Excel sheet")
        return None
