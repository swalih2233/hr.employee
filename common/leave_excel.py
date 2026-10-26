import logging
import os

from django.conf import settings
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
    "Annual Leave Balance",
    "Sick Leave Balance",
]


def get_approved_leaves_excel_path():
    reports_dir = os.path.join(settings.MEDIA_ROOT, "leave_reports")
    os.makedirs(reports_dir, exist_ok=True)
    return os.path.join(reports_dir, "approved_leaves.xlsx")


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
    user = getattr(profile, "user", None)
    name = user.get_full_name() if user else ""
    person_id = getattr(profile, "employe_id", None) or getattr(profile, "manager_id", None) or ""
    joining = _format_date(getattr(profile, "date_of_joining", None))
    return [
        name,
        person_id,
        profile.designation or "",
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
        getattr(profile, "available_leaves", 0),
        getattr(profile, "available_medical_leaves", 0),
    ]


def collect_approved_leave_rows():
    from employe.models import LeaveRequest
    from managers.models import UnifiedLeaveRequest

    rows = []

    employee_leaves = (
        LeaveRequest.objects.filter(status="Approved", is_withdrawn=False)
        .select_related("employee", "employee__user")
        .order_by("start_date", "id")
    )
    for leave in employee_leaves:
        if leave.employee:
            rows.append(_row_from_profile(leave.employee, "Employee", leave))

    manager_leaves = (
        UnifiedLeaveRequest.objects.filter(
            requested_by_role="manager",
            is_approved=True,
            is_withdrawn=False,
        )
        .select_related("manager", "manager__user")
        .order_by("start_date", "id")
    )
    for leave in manager_leaves:
        if leave.manager:
            rows.append(_row_from_profile(leave.manager, "Manager", leave))

    return rows


def write_approved_leaves_workbook(path, rows):
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

    widths = [28, 16, 22, 16, 12, 16, 36, 10, 22, 20]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    sheet.auto_filter.ref = sheet.dimensions
    sheet.freeze_panes = "A2"
    workbook.save(path)
    return path


def sync_approved_leaves_excel():
    """Rebuild the founder Excel sheet from all currently approved leaves."""
    try:
        path = get_approved_leaves_excel_path()
        rows = collect_approved_leave_rows()
        write_approved_leaves_workbook(path, rows)
        return path
    except Exception:
        logger.exception("Failed to update approved leaves Excel sheet")
        return None
