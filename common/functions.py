from datetime import date, datetime

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage


ANNUAL_LEAVE_FULL = 18.0
MEDICAL_LEAVE_FULL = 14.0
ANNUAL_LEAVE_PER_MONTH = 1.5
MEDICAL_LEAVE_PER_MONTH = 1.0
MID_MONTH_DAY = 16
HALF_MONTH_CREDIT = 0.5


def get_prorated_leave_allocation(joining_date, for_year=None):
    """
    Prorate first-year leave from joining date.

    Annual leave: 1.5 days per remaining month (18 / year).
    Sick leave: 1 day per remaining month (14 / year for a full calendar year).
    Joining on or after the 16th counts as a half month and adds 0.5.
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

    if joining_date.month == 1 and joining_date.day < MID_MONTH_DAY:
        return ANNUAL_LEAVE_FULL, MEDICAL_LEAVE_FULL

    remaining_after_join_month = 12 - joining_date.month
    if joining_date.day < MID_MONTH_DAY:
        month_credit = remaining_after_join_month + 1
        annual = month_credit * ANNUAL_LEAVE_PER_MONTH
        medical = month_credit * MEDICAL_LEAVE_PER_MONTH
    else:
        annual = remaining_after_join_month * ANNUAL_LEAVE_PER_MONTH + HALF_MONTH_CREDIT
        medical = remaining_after_join_month * MEDICAL_LEAVE_PER_MONTH + HALF_MONTH_CREDIT

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