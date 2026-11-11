from datetime import date, datetime

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage


ANNUAL_LEAVE_FULL = 18.0
MEDICAL_LEAVE_FULL = 14.0
ANNUAL_LEAVE_PER_MONTH = 1.5
MEDICAL_LEAVE_PER_MONTH = 1.0
MID_MONTH_DAY = 10
LATE_MONTH_DAY = 20
HALF_MONTH_CREDIT = 0.5


def get_prorated_leave_allocation(joining_date, for_year=None):
    """
    Prorate first-year leave from joining date:
    - Joining on or before the 10th (day <= 10): full month credit (+1.5 Annual, +1.0 Medical).
    - Joining mid-month (10 < day <= 20): half month credit (+0.5 Annual, +0.5 Medical).
    - Joining after 20 days (day > 20): no leave for that month (+0).
    """
    if isinstance(joining_date, str) and joining_date:
        try:
            joining_date = datetime.strptime(joining_date, "%Y-%m-%d").date()
        except ValueError:
            joining_date = None

    if not joining_date:
        return ANNUAL_LEAVE_FULL, MEDICAL_LEAVE_FULL

    for_year = for_year or date.today().year
    if joining_date.year < for_year:
        return ANNUAL_LEAVE_FULL, MEDICAL_LEAVE_FULL
    if joining_date.year > for_year:
        return 0.0, 0.0

    if joining_date.month == 1 and joining_date.day <= MID_MONTH_DAY:
        return ANNUAL_LEAVE_FULL, MEDICAL_LEAVE_FULL

    remaining_after_join_month = 12 - joining_date.month

    if joining_date.day <= MID_MONTH_DAY:
        # Full month credit for joining month
        annual = (remaining_after_join_month + 1) * ANNUAL_LEAVE_PER_MONTH
        medical = (remaining_after_join_month + 1) * MEDICAL_LEAVE_PER_MONTH
    elif joining_date.day <= LATE_MONTH_DAY:
        # Half month credit (0.5) for joining month
        annual = (remaining_after_join_month * ANNUAL_LEAVE_PER_MONTH) + HALF_MONTH_CREDIT
        medical = (remaining_after_join_month * MEDICAL_LEAVE_PER_MONTH) + HALF_MONTH_CREDIT
    else:
        # Joined after 20 days: no leave credit for joining month
        annual = remaining_after_join_month * ANNUAL_LEAVE_PER_MONTH
        medical = remaining_after_join_month * MEDICAL_LEAVE_PER_MONTH

    return min(annual, ANNUAL_LEAVE_FULL), min(medical, MEDICAL_LEAVE_FULL)


def generate_form_errors(form):
    message = ""
    for field in form:
        if field.errors:
            message += field.errors
    for err in form.non_field_errors():
        message += str(err)

    return message


def paginate_instances(request, instances, per_page=5):
    instances = Paginator(instances, per_page)
    page = request.GET.get('page', 1)

    try:
        instances = instances.page(page)
    except PageNotAnInteger:
        instances = instances.page(1)
    except EmptyPage:
        instances = instances.page(instances.num_pages)

    return instances