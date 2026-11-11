from django.shortcuts import render, reverse, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages 
from django.http.response import HttpResponseRedirect
import os
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
import traceback
from datetime import datetime, timedelta
import re

from common.decorators import allow_manager
from employe.models import *
from users.models import User, OTP
from managers.models import *

from django.utils import timezone
import smtplib
import ssl
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail, EmailMessage
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.http import FileResponse, JsonResponse
from django.contrib.auth.password_validation import validate_password
import random
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.validators import validate_email
import secrets
import logging
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum

logger = logging.getLogger(__name__)

# Google Calendar integration
from .google_calendar_service import get_google_calendar_service
from .forms import ManagerProfileForm, UnifiedLeaveRequestForm, AddUserForm, AddEmployeModelForm
from common.decorators import role_required, allow_founder
from common.utils import (
    get_user_role, is_founder, is_manager, get_user_profile,
    generate_manager_id, calculate_leave_days, build_founder_employee_table_rows,
    sync_employee_profile_from_related, get_employee_display_profile,
    get_half_day_info, format_leave_duration_display, get_user_display_name,
    sync_prorated_leave_if_needed, can_withdraw_leave, get_employees_under_manager,
)

logger = logging.getLogger(__name__)

# ==================== EMAIL FUNCTIONS ====================

def send_leave_notification(request, leave, email_type, recipient_email, manager_name=None, cc_founder=False):
    """
    Generic function to send leave notifications.
    - `leave`: The leave request object (LeaveRequest or UnifiedLeaveRequest).
    - `email_type`: 'new_request', 'approved', 'rejected', or 'submission_confirmation'.
    - `recipient_email`: The email address of the recipient.
    - `manager_name`: The name of the manager (for notifications to managers).
    - `cc_founder`: If True, CC the founder on the email.
    """
    
    if isinstance(leave, LeaveRequest):
        requester_profile = getattr(leave, 'employee', None)
        requester_name = (requester_profile.user.get_full_name() or requester_profile.user.username) if requester_profile and requester_profile.user else ""
        leave_model_name = 'LeaveRequest'
    elif isinstance(leave, UnifiedLeaveRequest):
        if leave.requested_by_role == 'manager' and leave.manager:
            requester_profile = leave.manager
            requester_name = (leave.manager.user.get_full_name() or leave.manager.user.username) if leave.manager.user else ""
        elif leave.employee:
            requester_profile = leave.employee
            requester_name = (leave.employee.user.get_full_name() or leave.employee.user.username) if leave.employee.user else ""
        else:
            requester_profile = leave.manager
            requester_name = (leave.manager.user.get_full_name() or leave.manager.user.username) if leave.manager and leave.manager.user else "Unknown"
        leave_model_name = 'UnifiedLeaveRequest'
    else:
        logger.error(f"Unknown leave model type: {type(leave)}")
        return

    # Calculate current balance leaves for email notification
    def _format_leave_num(v):
        try:
            val = float(v if v is not None else 0)
            return str(int(val)) if val == int(val) else ("%s" % val).rstrip("0").rstrip(".")
        except (ValueError, TypeError):
            return "0"

    annual_balance = _format_leave_num(getattr(requester_profile, 'available_leaves', 0))
    medical_balance = _format_leave_num(getattr(requester_profile, 'available_medical_leaves', 0))
    cf_balance = _format_leave_num(getattr(requester_profile, 'carryforward_available_leaves', 0))

    applied_leave_type = getattr(leave, 'leave_type', None)
    is_sick_leave = (applied_leave_type == 'ML')
    if is_sick_leave:
        applied_type_name = "Sick Leave"
        applied_leave_balance = medical_balance
    else:
        applied_type_name = "Annual Leave"
        applied_leave_balance = annual_balance

    if email_type in ['new_request', 'new_manager_request']:
        subject = f"New Leave Request from {requester_name}"
    elif email_type == 'approved':
        subject = "Your Leave Request has been Approved"
    elif email_type == 'rejected':
        subject = "Your Leave Request has been Rejected"
    elif email_type == 'cancelled':
        subject = f"Leave Request Cancelled by {requester_name}"
    elif email_type == 'withdrawal_requested':
        subject = f"Leave Withdrawal Request from {requester_name}"
    elif email_type == 'withdrawal_approved':
        subject = "Your Leave Withdrawal Request has been Approved"
    elif email_type == 'withdrawal_rejected':
        subject = "Your Leave Withdrawal Request has been Rejected"
    elif email_type == 'submission_confirmation':
        subject = "Leave Application Submitted Successfully (Pending)"
    else:
        subject = "Leave Request Update"

    if email_type in ['new_request', 'new_manager_request', 'withdrawal_requested', 'cancelled']:
        if leave_model_name == 'LeaveRequest':
            if getattr(leave, 'employee', None) and leave.employee.reporting_employee and recipient_email == leave.employee.reporting_employee.user.email:
                review_path = reverse('employe:subordinate_leave_requests')
            else:
                review_path = reverse('managers:leavelist')
        else:
            review_path = reverse('managers:manager_leave_requests_list')
        review_url = request.build_absolute_uri(review_path) if request else review_path
    elif email_type in ['approved', 'rejected', 'submission_confirmation', 'withdrawal_approved', 'withdrawal_rejected']:
        if leave_model_name == 'LeaveRequest':
            review_path = reverse('employe:leavelist')
        else:
            review_path = reverse('managers:manager_leave_history')
        review_url = request.build_absolute_uri(review_path) if request else review_path
    else:
        review_url = None

    html_content = render_to_string('emails/leave_notification.html', {
        'leave': leave,
        'employee': requester_profile,
        'requester_name': requester_name,
        'email_type': email_type,
        'status': leave.status,
        'manager_name': manager_name,
        'review_url': review_url,
        'half_day_info': get_half_day_info(leave),
        'leave_duration_display': format_leave_duration_display(leave),
        'annual_leave_balance': annual_balance,
        'medical_leave_balance': medical_balance,
        'carryforward_balance': cf_balance,
        'applied_type_name': applied_type_name,
        'applied_leave_balance': applied_leave_balance,
        'is_sick_leave': is_sick_leave,
    })

    try:
        cc_list = []
        if cc_founder:
            # CC all founders to ensure every founder account receives the notification
            founders = Founder.objects.all()
            for founder in founders:
                founder_email = getattr(getattr(founder, 'user', None), 'email', None)
                if founder_email and founder_email not in cc_list:
                    cc_list.append(founder_email)

        # If it's a new request or a cancellation and the requester has a founder, 
        # that founder should be the primary recipient if no manager is assigned
        actual_recipient = recipient_email
        if email_type in ['new_request', 'new_manager_request', 'cancelled']:
            requester_founder = None
            if isinstance(leave, LeaveRequest):
                requester_founder = getattr(leave.employee, 'founder', None) if getattr(leave, 'employee', None) else None
            elif isinstance(leave, UnifiedLeaveRequest):
                if leave.employee:
                    requester_founder = getattr(leave.employee, 'founder', None)
                elif leave.manager:
                    requester_founder = getattr(leave.manager, 'founder', None)
            
            if requester_founder:
                founder_email = getattr(getattr(requester_founder, 'user', None), 'email', None)
                if founder_email:
                    # If we don't have a recipient email, or if it's already set to founder
                    if not actual_recipient or actual_recipient == founder_email:
                        actual_recipient = founder_email
                    
                    # If founder is the recipient, we don't need to CC them
                    if isinstance(actual_recipient, str) and actual_recipient == founder_email:
                        if actual_recipient in cc_list:
                            cc_list.remove(actual_recipient)
                    elif isinstance(actual_recipient, (list, tuple)) and founder_email in actual_recipient:
                        if founder_email in cc_list:
                            cc_list.remove(founder_email)

        # Final check: if we still don't have a recipient but have CCs, use first CC as recipient
        if not actual_recipient and cc_list:
            actual_recipient = cc_list.pop(0)

        if not actual_recipient:
            logger.warning(f"No recipient found for leave notification '{email_type}'")
            return

        # Ensure actual_recipient is a list for EmailMessage 'to' field
        if isinstance(actual_recipient, str):
            recipient_list = [actual_recipient]
        elif isinstance(actual_recipient, (list, tuple)):
            recipient_list = list(actual_recipient)
        else:
            recipient_list = [str(actual_recipient)]

        # Clean recipient_list and cc_list
        recipient_list = [e.strip() for e in recipient_list if e and isinstance(e, str) and '@' in e]
        cc_list = [e.strip() for e in cc_list if e and isinstance(e, str) and '@' in e and e not in recipient_list]

        if not recipient_list:
            if cc_list:
                recipient_list = [cc_list.pop(0)]
            else:
                logger.warning(f"No valid recipient email address found for leave notification '{email_type}'")
                return

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None)
        clean_user = getattr(settings, 'EMAIL_HOST_USER', 'mavendoer802@gmail.com').strip()
        clean_pass = (getattr(settings, 'EMAIL_HOST_PASSWORD', '') or '').replace(' ', '').strip()
        all_recipients = list(recipient_list) + [c for c in cc_list if c not in recipient_list]

        # Construct MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email or clean_user
        msg['To'] = ', '.join(recipient_list)
        if cc_list:
            msg['Cc'] = ', '.join(cc_list)
        msg.attach(MIMEText(html_content, 'html'))
        msg_str = msg.as_string()

        sent_successfully = False
        smtp_errors = []

        # Attempt sending: Port 465 SSL, then Port 587 TLS
        for label, port, is_ssl in [('Port 465 SSL', 465, True), ('Port 587 TLS', 587, False)]:
            server = None
            try:
                context = ssl.create_default_context()
                if is_ssl:
                    server = smtplib.SMTP_SSL('smtp.gmail.com', port, context=context, timeout=15)
                else:
                    server = smtplib.SMTP('smtp.gmail.com', port, timeout=15)
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()

                server.set_debuglevel(0)

                # Attempt authentication (standard login, or AUTH LOGIN fallback)
                try:
                    server.login(clean_user, clean_pass)
                except (smtplib.SMTPServerDisconnected, smtplib.SMTPAuthenticationError) as auth_err:
                    logger.warning(f"{label} login encountered {auth_err}, retrying with AUTH LOGIN...")
                    if server:
                        try:
                            server.close()
                        except Exception:
                            pass
                    if is_ssl:
                        server = smtplib.SMTP_SSL('smtp.gmail.com', port, context=context, timeout=15)
                    else:
                        server = smtplib.SMTP('smtp.gmail.com', port, timeout=15)
                        server.ehlo()
                        server.starttls(context=context)
                        server.ehlo()
                    server.set_debuglevel(0)

                    code, resp = server.docmd("AUTH", "LOGIN")
                    if code == 334:
                        code, resp = server.docmd(base64.b64encode(clean_user.encode()).decode())
                        if code == 334:
                            code, resp = server.docmd(base64.b64encode(clean_pass.encode()).decode())
                    if code not in (235, 503):
                        raise smtplib.SMTPAuthenticationError(code, resp)

                server.sendmail(msg['From'], all_recipients, msg_str)
                logger.info(f"Leave notification '{email_type}' sent successfully via {label} to {recipient_list}")
                sent_successfully = True
                break
            except Exception as conn_err:
                logger.warning(f"Failed to send email via {label}: {conn_err}")
                smtp_errors.append(f"{label}: {conn_err}")
            finally:
                if server:
                    try:
                        server.quit()
                    except Exception:
                        pass

        if not sent_successfully:
            logger.error(f"Failed to send email to {recipient_email}. Errors: {' | '.join(smtp_errors)}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}", exc_info=True)




@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def index(request):
    user_role = get_user_role(request.user)
    if user_role == 'founder':
        return redirect(reverse('managers:founder_dashboard'))
    elif user_role == 'manager':
        return redirect(reverse('managers:manager_dashboard'))
    else:
        return redirect(reverse('managers:login'))


@login_required(login_url='/managers/founder/login/')
@allow_founder
def founder_dashboard(request):
    from django.db.models import Q
    logged_in_founder = get_object_or_404(Founder, user=request.user)
    founders = Founder.objects.all()
    managers = Manager.objects.all()
    
    # Get all employees (managers are listed separately in the Managers List section)
    employes = list(Employe.objects.all().select_related('user', 'manager', 'manager__user', 'founder', 'founder__user'))
    unified_employees = build_founder_employee_table_rows(employes)

    all_managers = list(Manager.objects.all().select_related('user', 'reporting_manager_profile__user', 'founder__user'))
    sub_managers = all_managers

    holidays = Holiday.objects.all()

    manager_leave_requests = UnifiedLeaveRequest.objects.filter(
        Q(requested_by_role='manager', is_approved=False, is_rejected=False, is_cancelled=False) |
        Q(requested_by_role='manager', is_withdrawal_requested=True)
    ).select_related('manager__user').order_by('-created_date')[:5]

    employee_leave_requests = LeaveRequest.objects.filter(
        Q(status='Pending', is_cancelled=False) |
        Q(is_withdrawal_requested=True, is_withdrawn=False, withdrawal_rejected=False)
    ).select_related('employee', 'employee__user').distinct().order_by('-created_date')[:5]

    recent_approved_leaves = []
    recent_manager_leaves = UnifiedLeaveRequest.objects.filter(
        requested_by_role='manager',
        is_approved=True
    ).select_related('manager__user', 'approved_by').order_by('-id')[:5]

    for leave in recent_manager_leaves:
        recent_approved_leaves.append({
            'requester_name': f"{leave.manager.user.first_name} {leave.manager.user.last_name}",
            'requested_by_role': 'manager',
            'manager': leave.manager,
            'subject': leave.subject,
            'start_date': leave.start_date,
            'end_date': leave.end_date,
            'total_days': leave.leave_duration,
            'leave_record': leave,
            'approved_by_name': get_user_display_name(leave.approved_by),
            'approval_date': leave.approval_date,
        })

    recent_employee_leaves = LeaveRequest.objects.filter(
        status='Approved'
    ).select_related('employee__user', 'approved_by').order_by('-id')[:5]

    for leave in recent_employee_leaves:
        recent_approved_leaves.append({
            'requester_name': f"{leave.employee.user.first_name} {leave.employee.user.last_name}",
            'requested_by_role': 'employee',
            'employee': leave.employee,
            'subject': leave.subject,
            'start_date': leave.start_date,
            'end_date': leave.end_date,
            'total_days': leave.leave_duration,
            'leave_record': leave,
            'approved_by_name': get_user_display_name(leave.approved_by),
            'approval_date': leave.approval_date,
        })

    recent_approved_leaves = recent_approved_leaves[:5]

    # Forms for adding new users
    user_form = AddUserForm()
    employe_form = AddEmployeModelForm()

    pending_manager_leaves_count = UnifiedLeaveRequest.objects.filter(
        requested_by_role='manager',
        is_approved=False,
        is_rejected=False,
        is_cancelled=False
    ).count()

    pending_employee_leaves_count = LeaveRequest.objects.filter(
        status='Pending',
        is_cancelled=False
    ).count()

    context = {
        'founder': logged_in_founder,
        'founders': founders,
        'managers': managers,
        'employees': unified_employees,
        'holidays': holidays,
        'f_count': founders.count(),
        'm_count': len(all_managers),
        'e_count': len(employes),
        'h_count': holidays.count(),
        'manager_leave_requests': manager_leave_requests,
        'employee_leave_requests': employee_leave_requests,
        'recent_approved_leaves': recent_approved_leaves,
        'pending_manager_leaves': pending_manager_leaves_count,
        'pending_employee_leaves': pending_employee_leaves_count,
        'user_form': user_form,
        'employe_form': employe_form,
    }

    return render(request, 'managers/founder_dashboard.html', context)


@login_required(login_url='/managers/founder/login/')
@allow_founder
def download_approved_leaves_excel(request):
    import io
    from common.leave_excel import (
        collect_approved_leave_rows,
        get_approved_leaves_excel_path,
        sync_approved_leaves_excel,
        write_approved_leaves_workbook,
    )

    filter_date = request.GET.get('date') or request.GET.get('filter_date')
    to_date = request.GET.get('to_date') or request.GET.get('end_date')

    # If date filter is provided, generate filtered Excel dynamically with matching records
    if filter_date or to_date:
        rows = collect_approved_leave_rows(
            filter_date=filter_date,
            start_date=filter_date,
            end_date=to_date,
        )
        buffer = io.BytesIO()
        write_approved_leaves_workbook(buffer, rows)
        date_str = f"{filter_date}_to_{to_date}" if (filter_date and to_date) else (filter_date or to_date)
        filename = f"approved_leaves_{date_str}.xlsx"
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # Full Excel file with all current and previous employees' approved leaves
    path = sync_approved_leaves_excel() or get_approved_leaves_excel_path()
    if not path or not os.path.exists(path):
        messages.error(request, "Approved leaves Excel sheet could not be created.")
        return redirect(reverse("managers:founder_dashboard"))

    return FileResponse(
        open(path, "rb"),
        as_attachment=True,
        filename="approved_leaves.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@login_required(login_url='/managers/founder/login/')
@allow_founder
def approved_leaves_table(request):
    from urllib.parse import urlencode
    from common.leave_excel import HEADERS, collect_approved_leave_rows, sync_approved_leaves_excel

    filter_date = request.GET.get('date') or request.GET.get('filter_date') or ''
    to_date = request.GET.get('to_date') or request.GET.get('end_date') or ''

    # Only full sync when no filter applied
    if not filter_date and not to_date:
        sync_approved_leaves_excel()

    rows = collect_approved_leave_rows(
        filter_date=filter_date or None,
        start_date=filter_date or None,
        end_date=to_date or None,
    )

    download_params = {}
    if filter_date:
        download_params['date'] = filter_date
    if to_date:
        download_params['to_date'] = to_date
    download_query = urlencode(download_params) if download_params else ''

    return render(request, "managers/approved_leaves_table.html", {
        "headers": HEADERS,
        "rows": rows,
        "filter_date": filter_date,
        "to_date": to_date,
        "download_query": download_query,
    })


@login_required(login_url='/managers/login')
@role_required('manager')
def manager_dashboard(request):
    try:
        manager = Manager.objects.get(user=request.user)
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found.")
        return redirect(reverse('managers:login'))

    # The form submission is now handled by the `add_employe` view via AJAX.
    # This view now only needs to prepare the context for the dashboard.
    user_form = AddUserForm()
    employe_form = AddEmployeModelForm()

    from common.utils import get_employees_under_manager
    employees = get_employees_under_manager(manager)

    employees_with_status = []
    today = timezone.now().date()
    for emp in employees:
        # Check if the object is an Employe or a Manager
        is_manager_obj = isinstance(emp, Manager)
        
        if is_manager_obj:
            is_on_leave = UnifiedLeaveRequest.objects.filter(
                manager=emp,
                is_approved=True,
                is_withdrawn=False,
                start_date__lte=today,
                end_date__gte=today
            ).exists()
        else:
            is_on_leave = LeaveRequest.objects.filter(
                employee=emp,
                status='Approved',
                is_withdrawn=False,
                start_date__lte=today,
                end_date__gte=today
            ).exists()

        status_text = ''
        status_class = ''

        if is_on_leave:
            status_text = 'On Leave'
            status_class = 'bg-yellow-100 text-yellow-800'
        else:
            if not is_manager_obj:
                status_text = emp.get_employe_status_display() or 'Active'
            else:
                status_text = 'Active' # Managers don't have employe_status field

            if status_text == 'ACTIVE' or status_text == 'Active':
                status_class = 'bg-green-100 text-green-800'
            elif status_text == 'PROBATION':
                status_class = 'bg-blue-100 text-blue-800'
            elif status_text == 'LEAVE':
                status_class = 'bg-red-100 text-red-800'
            else: # Default for 'Active'
                status_class = 'bg-green-100 text-green-800'

        employees_with_status.append({
            'employee': emp,
            'is_manager': is_manager_obj,
            'status': status_text,
            'status_class': status_class,
        })

    # Separate standard employees for LeaveRequest filter
    std_employees = [e for e in employees if not isinstance(e, Manager)]
    
    direct_employees = [e for e in std_employees if not getattr(e, 'reporting_employee_id', None)]
    pending_employee_requests = LeaveRequest.objects.filter(
        Q(employee__in=direct_employees, status='Pending', is_cancelled=False) |
        Q(employee__in=direct_employees, is_withdrawal_requested=True, is_withdrawn=False, withdrawal_rejected=False)
    ).order_by('-created_date')

    # Also include sub-manager requests in notification count if needed
    sub_managers = [e for e in employees if isinstance(e, Manager)]
    pending_sub_manager_requests = UnifiedLeaveRequest.objects.filter(
        manager__in=sub_managers,
        is_approved=False,
        is_rejected=False,
        is_cancelled=False
    )
    
    total_pending_count = pending_employee_requests.count() + pending_sub_manager_requests.count()

    manager_leave_requests = UnifiedLeaveRequest.objects.filter(
        Q(manager=manager, requested_by_role='manager', is_approved=False, is_rejected=False, is_cancelled=False) |
        Q(manager=manager, requested_by_role='manager', is_withdrawal_requested=True, is_withdrawn=False, withdrawal_rejected=False)
    ).order_by('-created_date')[:5]

    manager_leaves = UnifiedLeaveRequest.objects.filter(
        manager=manager,
        requested_by_role='manager'
    ).order_by('-created_date')[:5]

    recent_approved_employee_leaves = LeaveRequest.objects.filter(
        employee__in=std_employees,
        status='Approved'
    ).order_by('-created_date')[:5]
    
    leave_history = LeaveRequest.objects.filter(employee__in=std_employees).order_by('-created_date')

    # Recalculate duration for display in dashboard
    for leave in pending_employee_requests:
        leave.leave_duration = leave.calculate_working_days()
    for leave in manager_leave_requests:
        leave.leave_duration = leave.calculate_working_days()
    for leave in manager_leaves:
        leave.leave_duration = leave.calculate_working_days()
    for leave in recent_approved_employee_leaves:
        leave.leave_duration = leave.calculate_working_days()
    for leave in leave_history:
        leave.leave_duration = leave.calculate_working_days()
    
    holidays = Holiday.objects.all().order_by('date')

    # Refresh counts to be sure
    manager.recalculate_leave_counts()

    # Calculate remaining leaves for the manager
    annual_remaining = manager.available_leaves
    medical_remaining = manager.available_medical_leaves

    context = {
        'manager': manager,
        'employees': employees_with_status,
        'holidays': holidays,
        'employee_count': len(employees),
        'pending_employee_requests': pending_employee_requests,
        'pending_count': total_pending_count,
        'manager_leave_requests': manager_leave_requests,
        'recent_approved_employee_leaves': recent_approved_employee_leaves,
        'leave_history': leave_history,
        'leave_requests': pending_employee_requests,
        'manager_leaves': manager_leaves,
        'notification_count': total_pending_count,
        'user_form': user_form,
        'employe_form': employe_form,
        'annual_remaining': annual_remaining,
        'medical_remaining': medical_remaining,
    }

    return render(request, 'managers/manager_dashboard.html', context)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def approve_employee_leave(request, leave_id):
    leave_request = get_object_or_404(LeaveRequest, id=leave_id)
    employee_profile = leave_request.employee

    if request.method == 'POST':
        can_approve = False
        if request.user.is_superuser:
            can_approve = True
        elif is_founder(request.user):
            # Founders can approve any employee leave
            can_approve = True
        elif is_manager(request.user):
            # Team employees reporting to another employee are actioned by that employee
            if employee_profile.reporting_employee:
                messages.error(request, "This leave is handled by the employee's reporting supervisor.")
                return redirect('managers:leavelist')
            # Managers can only approve leaves for their own employees
            if employee_profile.manager and employee_profile.manager.user == request.user:
                can_approve = True
            else:
                messages.error(request, "Managers can only approve leaves for their own employees.")
                return redirect('managers:leavelist')
        elif employee_profile.reporting_employee and employee_profile.reporting_employee.user == request.user:
            can_approve = True

        if not can_approve:
            messages.error(request, "You do not have permission to approve this leave request.")
            return redirect('managers:leavelist')

        leave_days = calculate_leave_days(
            leave_request.start_date, leave_request.end_date, leave_request.is_half_day
        )

        if leave_request.leave_type == 'ML':
            employee_profile.medical_leaves_taken += leave_days
            employee_profile.available_medical_leaves -= leave_days
        elif leave_request.leave_type == 'AL':
            # Carry-forward deduction logic
            cf_eligible_days = 0
            
            # Get holidays within range
            from employe.models import Holiday # Local import to avoid potential circularity if not already imported correctly
            holidays = Holiday.objects.filter(date__range=[leave_request.start_date, leave_request.end_date]).values_list('date', flat=True)
            
            if leave_request.is_half_day:
                curr = leave_request.start_date
                if curr.weekday() < 5 and curr not in holidays and curr.month <= 3:
                    cf_eligible_days = 0.5
            else:
                curr = leave_request.start_date
                while curr <= leave_request.end_date:
                    if curr.weekday() < 5 and curr not in holidays:
                        if curr.month <= 3:
                            cf_eligible_days += 1
                    curr += timedelta(days=1)
            
            cf_available = employee_profile.carryforward_available_leaves
            
            # More robust check: how much CF is actually available from the grant
            from django.db.models import Sum
            other_cf_used = LeaveRequest.objects.filter(
                employee=employee_profile, 
                status='Approved',
                is_withdrawn=False,
            ).exclude(id=leave_request.id).aggregate(total=Sum('carryforward_used'))['total'] or 0
            
            cf_available_from_grant = max(0, employee_profile.carryforward_granted - other_cf_used)
            cf_to_use = min(cf_eligible_days, cf_available_from_grant)
            
            leave_request.carryforward_used = cf_to_use
            # employee_profile fields will be updated by recalculate_leave_counts() below
            
        employee_profile.save()

        leave_request.status = 'Approved'
        leave_request.is_approved = True
        leave_request.approved_by = request.user
        leave_request.approval_date = timezone.now()
        leave_request.leave_duration = leave_days
        leave_request.save()

        employee_profile.recalculate_leave_counts()

        from common.leave_excel import sync_approved_leaves_excel
        sync_approved_leaves_excel()

        send_leave_notification(request, leave_request, 'approved', leave_request.employee.user.email, cc_founder=True)

        messages.success(request, f"Leave request for {leave_request.employee.user.get_full_name()} approved.")
        if is_founder(request.user):
            return redirect('managers:founder_dashboard')
        if employee_profile.reporting_employee and employee_profile.reporting_employee.user == request.user:
            return redirect('employe:subordinate_leave_requests')
        return redirect('managers:leavelist')

    if is_founder(request.user):
        return redirect('managers:founder_dashboard')
    if employee_profile.reporting_employee and employee_profile.reporting_employee.user == request.user:
        return redirect('employe:subordinate_leave_requests')
    return redirect('managers:leavelist')


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def reject_employee_leave(request, leave_id):
    leave_request = get_object_or_404(LeaveRequest, id=leave_id)
    employee_profile = leave_request.employee

    if request.method == 'POST':
        can_reject = False
        if request.user.is_superuser:
            can_reject = True
        elif is_founder(request.user):
            # Founders can reject any employee leave
            can_reject = True
        elif is_manager(request.user):
            if employee_profile.reporting_employee:
                messages.error(request, "This leave is handled by the employee's reporting supervisor.")
                return redirect('managers:leavelist')
            # Managers can only reject leaves for their own employees
            if employee_profile.manager and employee_profile.manager.user == request.user:
                can_reject = True
            else:
                messages.error(request, "Managers can only reject leaves for their own employees.")
                return redirect('managers:leavelist')
        elif employee_profile.reporting_employee and employee_profile.reporting_employee.user == request.user:
            can_reject = True

        if not can_reject:
            messages.error(request, "You do not have permission to reject this leave request.")
            if is_founder(request.user):
                return redirect('managers:founder_dashboard')
            return redirect('managers:leavelist')

        leave_request.status = 'Rejected'
        leave_request.is_rejected = True
        leave_request.rejection_date = timezone.now()
        leave_request.save()

        send_leave_notification(request, leave_request, 'rejected', leave_request.employee.user.email, cc_founder=True)

        messages.success(request, f"Leave request for {leave_request.employee.user.get_full_name()} rejected.")
        if is_founder(request.user):
            return redirect('managers:founder_dashboard')
        if employee_profile.reporting_employee and employee_profile.reporting_employee.user == request.user:
            return redirect('employe:subordinate_leave_requests')
        return redirect('managers:leavelist')

    if is_founder(request.user):
        return redirect('managers:founder_dashboard')
    if employee_profile.reporting_employee and employee_profile.reporting_employee.user == request.user:
        return redirect('employe:subordinate_leave_requests')
    return redirect('managers:leavelist')


@login_required(login_url='/managers/login')
@role_required('manager')
def manager_apply_leave(request):
    if request.method == 'POST':
        form = UnifiedLeaveRequestForm(request.POST, request.FILES)
        if form.is_valid():
            leave_request = form.save(commit=False)
            if leave_request.is_half_day and leave_request.start_date != leave_request.end_date:
                messages.error(request, "Half-day leave must be for a single date (same start and end date).")
                return render(request, 'managers/apply_leave.html', {'form': form})
            if leave_request.is_half_day and leave_request.half_day_session not in ('AM', 'PM'):
                messages.error(request, "Please select Morning or Afternoon for half-day leave.")
                return render(request, 'managers/apply_leave.html', {'form': form})

            try:
                manager = Manager.objects.get(user=request.user)
                leave_request.manager = manager
                leave_request.requested_by_role = 'manager'
                leave_request.save()

                # Notify all founders
                send_leave_notification(request, leave_request, 'new_request', None, cc_founder=True)
                
                send_leave_notification(request, leave_request, 'submission_confirmation', request.user.email)

                messages.success(request, "Leave request submitted successfully!")
                return redirect(reverse("managers:manager_leave_history"))

            except Manager.DoesNotExist:
                messages.error(request, "Manager profile not found.")

    else:
        form = UnifiedLeaveRequestForm()

    return render(request, 'managers/apply_leave.html', {'form': form})


@login_required(login_url='/managers/login')
@role_required('manager')
def manager_cancel_leave(request, id):
    try:
        manager = Manager.objects.get(user=request.user)
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found.")
        return redirect(reverse('managers:login'))

    leave_request = get_object_or_404(UnifiedLeaveRequest, id=id, manager=manager, requested_by_role='manager')

    if leave_request.status != 'Pending':
        messages.error(request, f"Cannot cancel a leave request that is already {leave_request.status}.")
        return redirect(reverse('managers:manager_leave_history'))

    leave_request.is_cancelled = True
    leave_request.cancellation_date = timezone.now()
    leave_request.cancelled_by = request.user
    leave_request.save()

    # Notify all founders
    try:
        send_leave_notification(request, leave_request, 'cancelled', None, cc_founder=True)
    except Exception as e:
        logger.error(f"Failed to send cancellation notification: {e}")
        
        messages.success(request, "Leave request cancelled successfully!")
    except Exception as e:
        messages.warning(request, f"Leave cancelled, but failed to send notifications: {str(e)}")

    return redirect(reverse('managers:manager_leave_history'))


@login_required(login_url='/managers/founder/login/')
@allow_founder
def approve_manager_leave(request, id):
    leave_request = get_object_or_404(UnifiedLeaveRequest, id=id, requested_by_role='manager')
    manager = leave_request.manager

    # Check if the founder has permission to approve manager leave
    if not is_founder(request.user) and not request.user.is_superuser:
        messages.error(request, "Access denied. Only founders can approve manager leaves.")
        return redirect(reverse("managers:index"))

    actual_leave_days = calculate_leave_days(
        leave_request.start_date, leave_request.end_date, leave_request.is_half_day
    )

    if leave_request.leave_type == 'AL':
        # Carry-forward deduction logic
        cf_eligible_days = 0
        
        # Get holidays within range
        from employe.models import Holiday
        holidays = Holiday.objects.filter(date__range=[leave_request.start_date, leave_request.end_date]).values_list('date', flat=True)
        
        if leave_request.is_half_day:
            curr = leave_request.start_date
            if curr.weekday() < 5 and curr not in holidays and curr.month <= 3:
                cf_eligible_days = 0.5
        else:
            curr = leave_request.start_date
            while curr <= leave_request.end_date:
                if curr.weekday() < 5 and curr not in holidays:
                    if curr.month <= 3:
                        cf_eligible_days += 1
                curr += timedelta(days=1)
        
        # How much CF is actually available from the grant
        other_cf_used = UnifiedLeaveRequest.objects.filter(
            manager=manager, 
            is_approved=True,
            is_withdrawn=False,
        ).exclude(id=leave_request.id).aggregate(total=Sum('carryforward_used'))['total'] or 0
        
        cf_available_from_grant = max(0, manager.carryforward_granted - other_cf_used)
        cf_to_use = min(cf_eligible_days, cf_available_from_grant)
        
        leave_request.carryforward_used = cf_to_use

    leave_request.is_approved = True
    leave_request.is_rejected = False
    leave_request.approval_date = timezone.now()
    leave_request.approved_by = request.user
    leave_request.leave_duration = actual_leave_days
    leave_request.save()

    # Refresh leave counts
    manager.recalculate_leave_counts()

    from common.leave_excel import sync_approved_leaves_excel
    sync_approved_leaves_excel()

    send_leave_notification(request, leave_request, 'approved', manager.user.email, cc_founder=True)

    messages.success(request, f"Manager leave request approved successfully for {actual_leave_days} days.")
    return redirect(reverse("managers:founder_dashboard"))


@login_required(login_url='/managers/founder/login/')
@allow_founder
def reject_manager_leave(request, id):
    leave_request = get_object_or_404(UnifiedLeaveRequest, id=id, requested_by_role='manager')
    manager = leave_request.manager

    # Check if the founder has permission to reject manager leave
    if not is_founder(request.user) and not request.user.is_superuser:
        messages.error(request, "Access denied. Only founders can reject manager leaves.")
        return redirect(reverse("managers:index"))

    leave_request.is_rejected = True
    leave_request.is_approved = False
    leave_request.rejection_date = timezone.now()
    leave_request.rejected_by = request.user
    leave_request.save()

    send_leave_notification(request, leave_request, 'rejected', leave_request.manager.user.email, cc_founder=True)

    messages.success(request, "Manager leave request rejected successfully.")
    return redirect(reverse("managers:founder_dashboard"))


@login_required(login_url='/managers/login')
@role_required('manager')
def manager_withdraw_leave(request, id):
    manager = get_object_or_404(Manager, user=request.user)
    leave_request = get_object_or_404(UnifiedLeaveRequest, id=id, manager=manager, requested_by_role='manager')

    if not leave_request.is_approved:
        messages.error(request, "Only approved leaves can be withdrawn.")
        return redirect(reverse('managers:manager_leave_history'))

    if not can_withdraw_leave(leave_request):
        messages.error(request, "Leave can only be withdrawn within 7 days of approval.")
        return redirect(reverse('managers:manager_leave_history'))

    if request.method == 'POST':
        leave_request.is_withdrawal_requested = True
        leave_request.withdrawal_subject = request.POST.get('subject')
        leave_request.withdrawal_reason = request.POST.get('reason')
        leave_request.withdrawal_requested_date = timezone.now()
        leave_request.save()

        # Notify founders
        founders = Founder.objects.all()
        for founder in founders:
            send_leave_notification(request, leave_request, 'withdrawal_requested', founder.user.email)

        messages.success(request, "Withdrawal request submitted to founders.")
        return redirect(reverse('managers:manager_leave_history'))

    return render(request, 'employe/withdraw_leave.html', {
        'leave_request': leave_request,
        'manager': manager
    })


def _withdrawal_redirect(request):
    if is_founder(request.user):
        return redirect(reverse('managers:founder_dashboard'))
    next_target = request.POST.get('next') or ''
    if next_target == 'leavelist' or 'leavelist' in request.META.get('HTTP_REFERER', ''):
        return redirect(reverse('managers:leavelist'))
    return redirect(reverse('managers:manager_dashboard'))


def _can_action_withdrawal(request, leave_request, leave_type):
    if request.user.is_superuser or is_founder(request.user):
        return True
    if leave_type != 'employee':
        return False
    manager = Manager.objects.filter(user=request.user).first()
    if not manager:
        return False
    emp = leave_request.employee
    if getattr(emp, 'reporting_employee_id', None):
        return False
    return emp in get_employees_under_manager(manager)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def approve_withdrawal(request, id, leave_type):
    if leave_type == 'employee':
        leave_request = get_object_or_404(LeaveRequest, id=id)
        recipient_email = leave_request.employee.user.email
    else:
        leave_request = get_object_or_404(UnifiedLeaveRequest, id=id)
        if leave_request.manager:
            recipient_email = leave_request.manager.user.email
        elif leave_request.employee:
            recipient_email = leave_request.employee.user.email
        else:
            recipient_email = None

    if not _can_action_withdrawal(request, leave_request, leave_type):
        messages.error(request, "You do not have permission to approve this withdrawal request.")
        return _withdrawal_redirect(request)

    if request.method != 'POST':
        return _withdrawal_redirect(request)

    if leave_request.is_withdrawn:
        return _withdrawal_redirect(request)

    leave_request.is_withdrawn = True
    leave_request.is_withdrawal_requested = False
    leave_request.withdrawal_rejected = False
    leave_request.carryforward_used = 0
    leave_request.save()

    # Recalculate leave counts for the requester so counts return to normal automatically
    if leave_type == 'employee':
        leave_request.employee.recalculate_leave_counts()
        # CC founder if manager approves
        cc_founder = not is_founder(request.user)
        if recipient_email:
            send_leave_notification(request, leave_request, 'withdrawal_approved', recipient_email, cc_founder=cc_founder)
    else:
        if leave_request.manager:
            leave_request.manager.recalculate_leave_counts()
        elif leave_request.employee:
            leave_request.employee.recalculate_leave_counts()
        # CC founder if manager (or another founder) approves a manager's withdrawal
        if recipient_email:
            send_leave_notification(request, leave_request, 'withdrawal_approved', recipient_email, cc_founder=True)

    from common.leave_excel import sync_approved_leaves_excel
    sync_approved_leaves_excel()

    messages.success(request, "Withdrawal request approved.")
    return _withdrawal_redirect(request)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def reject_withdrawal(request, id, leave_type):
    if leave_type == 'employee':
        leave_request = get_object_or_404(LeaveRequest, id=id)
        recipient_email = leave_request.employee.user.email
    else:
        leave_request = get_object_or_404(UnifiedLeaveRequest, id=id)
        if leave_request.manager:
            recipient_email = leave_request.manager.user.email
        elif leave_request.employee:
            recipient_email = leave_request.employee.user.email
        else:
            recipient_email = None

    if not _can_action_withdrawal(request, leave_request, leave_type):
        messages.error(request, "You do not have permission to reject this withdrawal request.")
        return _withdrawal_redirect(request)

    if request.method != 'POST':
        return _withdrawal_redirect(request)

    leave_request.is_withdrawal_requested = False
    leave_request.withdrawal_rejected = True
    leave_request.save()

    # CC founder if manager rejects
    cc_founder = not is_founder(request.user)
    if recipient_email:
        send_leave_notification(request, leave_request, 'withdrawal_rejected', recipient_email, cc_founder=cc_founder)

    messages.success(request, "Withdrawal request rejected.")
    return _withdrawal_redirect(request)


@login_required(login_url='/managers/login')
@role_required('manager')
def manager_leave_history(request):
    try:
        manager = Manager.objects.get(user=request.user)
        # Refresh counts to be sure
        manager.recalculate_leave_counts()
        
        unified_requests = UnifiedLeaveRequest.objects.filter(
            manager=manager,
            requested_by_role='manager'
        ).order_by('-created_date')

        for leave_request in unified_requests:
            if leave_request.is_approved:
                leave_request.calculated_duration = leave_request.leave_duration
            else:
                leave_request.calculated_duration = calculate_leave_days(leave_request.start_date, leave_request.end_date)

        context = {
            'unified_requests': unified_requests,
            'manager': manager,
            'annual_remaining': manager.available_leaves,
            'medical_remaining': manager.available_medical_leaves,
            'total_taken': manager.leaves_taken + manager.medical_leaves_taken + manager.carryforward_leaves_taken,
        }
        return render(request, 'managers/leave_history.html', context)

    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found.")
        return redirect(reverse("managers:manager_dashboard"))


@login_required(login_url='/managers/login')
@allow_manager
def manager_leave_requests_list(request):
    if not is_founder(request.user):
        messages.error(request, "Access denied. Only founders can view manager leave requests.")
        return redirect(reverse("managers:index"))

    pending_requests = UnifiedLeaveRequest.objects.filter(
        requested_by_role='manager',
        is_approved=False,
        is_rejected=False,
        is_cancelled=False
    ).order_by('-created_date')

    for leave_request in pending_requests:
        leave_request.calculated_duration = calculate_leave_days(leave_request.start_date, leave_request.end_date)

    context = {
        'leave_requests': pending_requests,
        'is_founder': True
    }
    return render(request, 'managers/manager_leave_requests.html', context)


@login_required(login_url='/managers/founder/login/')
@allow_founder
def view_manager_leave_request(request, id):
    if not is_founder(request.user):
        messages.error(request, "Access denied. Only founders can view manager leave requests.")
        return redirect(reverse("managers:index"))

    leave_request = get_object_or_404(UnifiedLeaveRequest, id=id, requested_by_role='manager')
    leave_request.calculated_duration = calculate_leave_days(leave_request.start_date, leave_request.end_date)

    context = {
        'leave_request': leave_request,
        'manager': leave_request.manager,
        'is_founder': True
    }
    return render(request, 'managers/view_manager_leave.html', context)


@login_required(login_url='/managers/login')
@role_required('manager')
def leave_requests(request):
    try:
        manager = Manager.objects.get(user=request.user)
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found.")
        return redirect(reverse('managers:login'))

    from common.utils import get_employees_under_manager
    employees = [
        e for e in get_employees_under_manager(manager)
        if not isinstance(e, Manager) and not getattr(e, 'reporting_employee_id', None)
    ]

    pending_employee_requests = LeaveRequest.objects.filter(
        Q(employee__in=employees, status='Pending', is_cancelled=False) |
        Q(employee__in=employees, is_withdrawal_requested=True, is_withdrawn=False, withdrawal_rejected=False)
    ).order_by('-created_date')

    for leave in pending_employee_requests:
        leave.leave_duration = leave.calculate_working_days()

    context = {
        'leave_requests': pending_employee_requests,
        'manager': manager,
        'profile': manager,
        'notification_count': pending_employee_requests.count(),
    }
    return render(request, 'managers/leave_requests.html', context)


def login(request):
    # Consume all existing messages so they don't appear on the login page
    storage = messages.get_messages(request)
    for _ in storage:
        pass
        
    if request.method == "GET":
        return render(request, "managers/login.html", {"title": "Manager Login", "messages": []})
        
    context = {"title": "Manager Login"}
    
    if request.method == 'POST':
        manager_id = request.POST.get("manager_id")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if email and password and manager_id:
            user = authenticate(request, email=email, password=password)
            
            if user:
                try:
                    manager_profile = Manager.objects.get(user=user)
                    if manager_profile.manager_id != manager_id:
                        messages.error(request, "Invalid Manager ID for this account")
                        return render(request, "managers/login.html", {"title": "Manager Login", "messages": messages.get_messages(request)})
                    
                    auth_login(request, user)
                    user.is_manager = True
                    user.save()
                    return HttpResponseRedirect(reverse("managers:index"))
                except Manager.DoesNotExist:
                    if not user.is_superuser:
                        messages.error(request, "Manager profile not found")
                        return render(request, "managers/login.html", {"title": "Manager Login", "messages": messages.get_messages(request)})
                    else:
                        auth_login(request, user)
                        return HttpResponseRedirect(reverse("managers:index"))
            else:
                messages.error(request, "Invalid email or password")
        else:
            messages.error(request, "Manager ID, Email and password are required")

    return render(request, "managers/login.html", {"title": "Manager Login", "messages": messages.get_messages(request)})


def founder_login(request):
    # Consume all existing messages so they don't appear on the login page
    storage = messages.get_messages(request)
    for _ in storage:
        pass
        
    if request.method == "GET":
        return render(request, "managers/founder_login.html", {"title": "Founder Login", "messages": []})
        
    context = {"title": "Founder Login"}
    
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password")

        if email and password:
            user = authenticate(request, email=email, password=password)
            
            if user:
                if is_founder(user):
                    auth_login(request, user)
                    return HttpResponseRedirect(reverse("managers:index"))
                else:
                    messages.error(request, "Access restricted to founders only")
            else:
                messages.error(request, "Invalid email or password")
        else:
            messages.error(request, "Email and password are required")

    return render(request, "managers/founder_login.html", {"title": "Founder Login", "messages": messages.get_messages(request)})


def logout(request):
    auth_logout(request)
    return HttpResponseRedirect(reverse("managers:login"))


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def viewlist(request, id):
    leave_request = get_object_or_404(LeaveRequest, id=id)
    employe = leave_request.employee
    
    context = {
        'leave_request': leave_request,
        'employe': employe,
        'user': employe.user,
    }
    return render(request, 'managers/viewlist.html', context)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def approve_leave(request, pk):
    return approve_employee_leave(request, pk)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def reject_leave(request, pk):
    return reject_employee_leave(request, pk)


from common.utils import get_user_role, is_founder, is_manager, get_user_profile, generate_manager_id, calculate_leave_days

@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def add_employe(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        existing_user = User.objects.filter(email=email).first()
        
        if existing_user:
            # Check if this user already has an employee profile
            try:
                employe = Employe.objects.get(user=existing_user)
                # If they are already an employee, just update the manager/founder
                if is_manager(request.user):
                    try:
                        manager = Manager.objects.get(user=request.user)
                        employe.manager = manager
                        if manager.founder:
                            employe.founder = manager.founder
                    except Manager.DoesNotExist:
                        pass
                elif is_founder(request.user):
                    try:
                        founder = Founder.objects.get(user=request.user)
                        employe.founder = founder
                    except Founder.DoesNotExist:
                        pass
                
                # Update other fields if provided in POST
                employe.department = request.POST.get('department', employe.department)
                employe.designation = request.POST.get('designation', employe.designation)
                employe.work_location = request.POST.get('work_location', employe.work_location)
                if not employe.created_by:
                    employe.created_by = request.user
                employe.save()
                sync_employee_profile_from_related(employe)
                
                success_msg = f"✅ Existing employee {existing_user.get_full_name()} has been successfully assigned/updated!"
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({"status": "success", "message": success_msg})
                
                messages.success(request, success_msg)
                if is_founder(request.user):
                    return redirect(reverse('managers:founder_dashboard'))
                return redirect(reverse('managers:manager_dashboard'))
                
            except Employe.DoesNotExist:
                # User exists but is not an employee, create profile
                employe_form = AddEmployeModelForm(request.POST, request.FILES)
                if employe_form.is_valid():
                    employe = employe_form.save(commit=False)
                    employe.user = existing_user
                    
                    if is_manager(request.user):
                        try:
                            manager = Manager.objects.get(user=request.user)
                            employe.manager = manager
                            if manager.founder:
                                employe.founder = manager.founder
                        except Manager.DoesNotExist:
                            pass
                    elif is_founder(request.user):
                        try:
                            founder = Founder.objects.get(user=request.user)
                            employe.founder = founder
                        except Founder.DoesNotExist:
                            pass
                    
                    employe.created_by = request.user
                    employe.save()
                    success_msg = f"✅ Employee profile created for existing user {existing_user.get_full_name()}!"
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({"status": "success", "message": success_msg})
                    
                    messages.success(request, success_msg)
                    if is_founder(request.user):
                        return redirect(reverse('managers:founder_dashboard'))
                    return redirect(reverse('managers:manager_dashboard'))
                else:
                    errors = employe_form.errors
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({"status": "error", "message": "Form validation failed", "errors": errors})
                    messages.error(request, "Form validation failed")

        # Normal flow for new user
        user_form = AddUserForm(request.POST)
        employe_form = AddEmployeModelForm(request.POST, request.FILES)
        
        if user_form.is_valid() and employe_form.is_valid():
            try:
                user = user_form.save(commit=False)
                user.set_password(user_form.cleaned_data['password'])
                user.is_employee = True
                user.username = user_form.cleaned_data['email']
                user.save()

                employe = employe_form.save(commit=False)
                employe.user = user
                
                if is_manager(request.user):
                    try:
                        manager = Manager.objects.get(user=request.user)
                        employe.manager = manager
                        if manager.founder:
                            employe.founder = manager.founder
                    except Manager.DoesNotExist:
                        pass
                
                if is_founder(request.user):
                    try:
                        founder = Founder.objects.get(user=request.user)
                        employe.founder = founder
                    except Founder.DoesNotExist:
                        pass
                
                employe.save()
                
                # Set available carryforward if within Jan-Mar
                current_date = timezone.now().date()
                if current_date.month <= 3:
                    employe.carryforward_available_leaves = employe.carryforward_granted
                    employe.save()
                
                success_msg = f"✅ Employee {user.get_full_name()} created successfully!"
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({"status": "success", "message": success_msg})
                    
                messages.success(request, success_msg)
                if is_founder(request.user):
                    return redirect(reverse('managers:founder_dashboard'))
                return redirect(reverse('managers:manager_dashboard'))
                    
            except Exception as e:
                error_msg = f"Error creating employee: {str(e)}"
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({"status": "error", "message": error_msg})
                messages.error(request, error_msg)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {**user_form.errors, **employe_form.errors}
                return JsonResponse({"status": "error", "message": "Please correct the form errors.", "errors": errors})
                
            messages.error(request, "Please correct the form errors.")
            # Re-populate the context for the manager dashboard to show errors in the sidebar
            try:
                manager = Manager.objects.get(user=request.user)
            except Manager.DoesNotExist:
                messages.error(request, "Manager profile not found.")
                return redirect(reverse('managers:login'))

            from common.utils import get_employees_under_manager
            employees = get_employees_under_manager(manager)

            employees_with_status = []
            today = timezone.now().date()
            for emp in employees:
                is_on_leave = LeaveRequest.objects.filter(
                    employee=emp,
                    status='Approved',
                    is_withdrawn=False,
                    start_date__lte=today,
                    end_date__gte=today
                ).exists()

                status_text = ''
                status_class = ''

                if is_on_leave:
                    status_text = 'On Leave'
                    status_class = 'bg-yellow-100 text-yellow-800'
                else:
                    status_text = emp.get_employe_status_display() or 'Active'
                    if status_text == 'ACTIVE':
                        status_class = 'bg-green-100 text-green-800'
                    elif status_text == 'PROBATION':
                        status_class = 'bg-blue-100 text-blue-800'
                    elif status_text == 'LEAVE':
                        status_class = 'bg-red-100 text-red-800'
                    else: # Default for 'Active'
                        status_class = 'bg-green-100 text-green-800'

                employees_with_status.append({
                    'employee': emp,
                    'status': status_text,
                    'status_class': status_class,
                })

            pending_employee_requests = LeaveRequest.objects.filter(
                employee__in=employees,
                status='Pending'
            ).order_by('-created_date')

            manager_leave_requests = UnifiedLeaveRequest.objects.filter(
                manager=manager,
                requested_by_role='manager'
            ).order_by('-created_date')[:5]

            recent_approved_employee_leaves = LeaveRequest.objects.filter(
                employee__in=employees,
                status='Approved'
            ).order_by('-created_date')[:5]
            
            leave_history = LeaveRequest.objects.filter(employee__in=employees).order_by('-created_date')

            holidays = Holiday.objects.all().order_by('date')

            # Calculate remaining leaves for the manager
            total_annual_taken = UnifiedLeaveRequest.objects.filter(
                manager=manager,
                leave_type='AL',
                is_approved=True
            ).aggregate(total=Sum('leave_duration'))['total'] or 0

            total_medical_taken = UnifiedLeaveRequest.objects.filter(
                manager=manager,
                leave_type='ML',
                is_approved=True
            ).aggregate(total=Sum('leave_duration'))['total'] or 0

            annual_remaining = 18 - total_annual_taken
            medical_remaining = 14 - total_medical_taken

            context = {
                'manager': manager,
                'employees': employees_with_status,
                'holidays': holidays,
                'employee_count': len(employees),
                'pending_employee_requests': pending_employee_requests,
                'pending_count': pending_employee_requests.count(),
                'manager_leave_requests': manager_leave_requests,
                'recent_approved_employee_leaves': recent_approved_employee_leaves,
                'leave_history': leave_history,
                'leave_requests': pending_employee_requests,
                'manager_leaves': manager_leave_requests,
                'notification_count': pending_employee_requests.count(),
                'user_form': user_form,
                'employe_form': employe_form,
                'annual_remaining': annual_remaining,
                'medical_remaining': medical_remaining,
                'show_add_employee_sidebar': True,  # Flag to keep sidebar open
            }
            return render(request, 'managers/manager_dashboard.html', context)
    
    # If GET request, redirect to the dashboard, as this view only handles POST
    return redirect(reverse('managers:manager_dashboard'))


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def edit_employe(request, id):
    employe = get_object_or_404(Employe, id=id)
    user = employe.user
    
    if request.method == 'POST':
        try:
            # Update User fields
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.phone_number = request.POST.get('phone_number', user.phone_number)
            user.gender = request.POST.get('gender', user.gender)
            user.save()

            # Update Employee fields
            employe.employe_id = request.POST.get('employe_id', employe.employe_id)
            employe.department = request.POST.get('department', employe.department)
            employe.designation = request.POST.get('designation', employe.designation)
            employe.work_location = request.POST.get('work_location', employe.work_location)
            employe.employment_Type = request.POST.get('employment_Type', employe.employment_Type)
            
            date_of_joining = request.POST.get('date_of_joining')
            if date_of_joining:
                try:
                    employe.date_of_joining = datetime.strptime(date_of_joining, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    pass

            # Handle Image Upload
            if 'image' in request.FILES:
                employe.image = request.FILES['image']

            carryforward_granted = request.POST.get('carryforward_granted', 0)
            try:
                cf_granted = int(carryforward_granted)
                employe.carryforward_granted = cf_granted
                
                # Update available carryforward if within Jan-Mar
                current_date = timezone.now().date()
                if current_date.month <= 3:
                    employe.carryforward_available_leaves = max(0, cf_granted - employe.carryforward_leaves_taken)
            except (ValueError, TypeError):
                pass

            total_annual_input = request.POST.get('total_annual_leaves')
            if total_annual_input is not None and total_annual_input != '':
                try:
                    val = float(total_annual_input)
                    employe.available_leaves = max(0.0, val - (employe.leaves_taken or 0))
                except (ValueError, TypeError):
                    pass

            total_med_input = request.POST.get('total_medical_leaves')
            if total_med_input is not None and total_med_input != '':
                try:
                    val = float(total_med_input)
                    employe.available_medical_leaves = max(0.0, val - (employe.medical_leaves_taken or 0))
                except (ValueError, TypeError):
                    pass
                
            employe.save()
            messages.success(request, "Employee details updated successfully!")
            
            if is_founder(request.user):
                return redirect(reverse('managers:employees_list'))
            return redirect(reverse('managers:manager_dashboard'))
            
        except Exception as e:
            messages.error(request, f"Error updating employee: {str(e)}")
    
    context = {
        'employe': employe,
        'user': user,
    }
    return render(request, 'managers/edit_employe.html', context)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def details(request, id):
    from employe.models import Address, EmergencyContact, Benefits, WorkSchedule
    from managers.models import AddressManager, EmergencyContactManager, BenefitsManager, WorkScheduleManager

    employe = get_object_or_404(Employe, id=id)
    sync_employee_profile_from_related(employe)
    user = employe.user
    manager_profile = Manager.objects.filter(user=user).first()

    address = Address.objects.filter(employe=employe).first()
    contact = EmergencyContact.objects.filter(employe=employe).first()
    benefits = Benefits.objects.filter(employe=employe).first()
    workschedule = WorkSchedule.objects.filter(employe=employe).first()

    if manager_profile:
        if not address:
            address = AddressManager.objects.filter(manager=manager_profile).first()
        if not contact:
            contact = EmergencyContactManager.objects.filter(manager=manager_profile).first()
        if not benefits:
            benefits = BenefitsManager.objects.filter(manager=manager_profile).first()
        if not workschedule:
            workschedule = WorkScheduleManager.objects.filter(manager=manager_profile).first()

    display = get_employee_display_profile(employe)

    context = {
        'manager': employe,
        'user': user,
        'address': address,
        'contact': contact,
        'benefits': benefits,
        'workschedule': workschedule,
        'is_employee_view': True,
        'profile_display': display,
        'back_url': request.META.get('HTTP_REFERER', reverse('managers:manager_dashboard')),
    }
    return render(request, 'managers/details.html', context)


@login_required(login_url='/managers/founder/login/')
@allow_founder
def manager_full_details(request, id):
    manager_obj = get_object_or_404(Manager, id=id)
    
    try:
        address = AddressManager.objects.filter(manager=manager_obj).first()
    except:
        address = None
        
    try:
        contact = EmergencyContactManager.objects.filter(manager=manager_obj).first()
    except:
        contact = None
        
    try:
        benefits = BenefitsManager.objects.filter(manager=manager_obj).first()
    except:
        benefits = None
        
    try:
        workschedule = WorkScheduleManager.objects.filter(manager=manager_obj).first()
    except:
        workschedule = None

    context = {
        'manager': manager_obj,
        'user': manager_obj.user,
        'address': address,
        'contact': contact,
        'benefits': benefits,
        'workschedule': workschedule,
        'is_manager_view_by_founder': True,
        'back_url': request.META.get('HTTP_REFERER', reverse('managers:founder_dashboard')),
    }
    return render(request, 'managers/details.html', context)


@csrf_exempt
@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def delete_employee(request, id):
    employe = get_object_or_404(Employe, id=id)

    # Permission check
    is_allowed = False
    if request.user.is_superuser:
        is_allowed = True
    elif is_founder(request.user):
        is_allowed = True
    elif is_manager(request.user):
        try:
            # Check if the employee belongs to this manager
            if employe.manager and employe.manager.user == request.user:
                is_allowed = True
        except Manager.DoesNotExist:
            is_allowed = False

    if not is_allowed:
        return JsonResponse({'status': 'error', 'message': 'You do not have permission to delete this employee.'}, status=403)

    if request.method not in ['POST', 'DELETE']:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    try:
        employee_name = employe.user.get_full_name() or employe.user.email
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.method == 'DELETE'

        # Founders permanently delete duplicate/unwanted employee profiles
        if is_founder(request.user) or request.user.is_superuser:
            user = employe.user
            user.delete()
            message = f'Employee {employee_name} deleted successfully.'
            if is_ajax:
                return JsonResponse({'status': 'success', 'message': message})
            messages.success(request, message)
            return redirect('managers:founder_dashboard')

        # Managers only remove the employee from their team
        if employe.previous_manager:
            employe.manager = employe.previous_manager
            employe.previous_manager = None
            employe.save()
            message = f'Employee {employee_name} has been reassigned to {employe.manager.user.get_full_name()}.'
        else:
            employe.manager = None
            employe.save()
            message = f'Employee {employee_name} has been removed from your team.'

        if is_ajax:
            return JsonResponse({'status': 'success', 'message': message})
        messages.success(request, message)
        return redirect('/managers/employees/')
    except Exception as e:
        logger.error(f"Error deleting employee with id {id}: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)


@csrf_exempt
@login_required(login_url='/managers/founder/login/')
@allow_founder
def add_manager(request):
    if request.method == 'POST':
        try:
            manager_id = request.POST.get("manager_id")
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            email = request.POST.get("email")
            phone = request.POST.get("phone")
            password = request.POST.get("password")
            joining_date = request.POST.get("joining_date")
            job_role = request.POST.get("job_role")
            carryforward_granted = request.POST.get("carryforward_granted", 0)
            image = request.FILES.get("image")

            # check duplicate email
            if User.objects.filter(email=email).exists():
                return JsonResponse({"status": "error", "message": "Email already exists."})
            
            # check duplicate manager_id
            if Manager.objects.filter(manager_id=manager_id).exists():
                return JsonResponse({"status": "error", "message": "Manager ID already exists."})

            # create user
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
            )
            user.phone_number = phone
            user.is_manager = True
            user.save()

            # create manager profile
            current_founder = None
            if is_founder(request.user):
                try:
                    current_founder = Founder.objects.get(user=request.user)
                except Founder.DoesNotExist:
                    pass

            # Convert carryforward to int
            try:
                cf_granted = int(carryforward_granted)
            except (ValueError, TypeError):
                cf_granted = 0

            manager = Manager.objects.create(
                user=user,
                manager_id=manager_id,
                founder=current_founder,
                date_of_joining=joining_date,
                designation=job_role,
                image=image,
                carryforward_granted=cf_granted,
            )

            # Set available carryforward if within Jan-Mar
            current_date = timezone.now().date()
            if current_date.month <= 3:
                manager.carryforward_available_leaves = cf_granted
                manager.save()

            return JsonResponse({"status": "success", "message": "Manager added successfully."})
        except Exception as e:
            logger.error(f"Error adding manager: {e}", exc_info=True)
            return JsonResponse({"status": "error", "message": str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required(login_url='/managers/founder/login/')
@allow_founder
def delete_manager(request, id):
    manager = get_object_or_404(Manager, id=id)
    if request.method == 'POST':
        # Check ownership
        if not is_founder(request.user) and not request.user.is_superuser:
            return JsonResponse({'status': 'error', 'message': 'You do not have permission to delete this manager.'})

        try:
            manager.user.delete()
            return JsonResponse({'status': 'success', 'message': 'Manager deleted successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@login_required(login_url='/managers/founder/login/')
@allow_founder
def founder_add(request):
    if request.method == 'POST':
        try:
            # Basic validation
            required_fields = ['first_name', 'last_name', 'email', 'password']
            errors = {field: f"{field.replace('_', ' ').title()} is required." for field in required_fields if not request.POST.get(field)}

            if User.objects.filter(email=request.POST.get('email')).exists():
                errors['email'] = "A user with this email already exists."

            if errors:
                return JsonResponse({'status': 'error', 'errors': errors}, status=400)

            user = User.objects.create_user(
                username=request.POST['email'],
                email=request.POST['email'],
                password=request.POST['password'],
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name'],
                phone_number=request.POST.get('phone', ''),
                is_superuser=True,
                is_staff=True
            )
            
            founder = Founder.objects.create(
                user=user,
                date_of_joining=request.POST.get('joining_date'),
                designation=request.POST.get('job_role', ''),
            )
            
            if request.FILES.get('image'):
                founder.image = request.FILES['image']
                founder.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f"Founder {user.get_full_name()} added successfully!",
                'founder': {
                    'id': founder.id,
                    'full_name': user.get_full_name(),
                    'email': user.email,
                    'image_url': founder.image.url if founder.image else '/static/images/default-avatar.png'
                }
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"An unexpected error occurred: {str(e)}"}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required(login_url='/managers/founder/login/')
@allow_founder
def delete_founder(request, id):
    founder = get_object_or_404(Founder, id=id)
    if request.method == 'POST':
        try:
            founder.user.delete()
            return JsonResponse({'status': 'success', 'message': 'Founder deleted successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def holidays_list(request):
    from employe.models import Holiday
    holidays = Holiday.objects.all().order_by('date')
    
    context = {
        'holidays': holidays,
    }
    return render(request, 'managers/holidays_list.html', context)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def add_holiday(request):
    from employe.models import Holiday
    
    if request.method == 'POST':
        try:
            holiday = Holiday.objects.create(
                title=request.POST['title'],
                date=request.POST['date']
            )
            messages.success(request, f"Holiday '{holiday.title}' added successfully!")
            return redirect(reverse('managers:holidays_list'))
        except Exception as e:
            messages.error(request, f"Error adding holiday: {str(e)}")
    
    return render(request, 'managers/add_holiday.html')


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def delete_holiday(request, id):
    from employe.models import Holiday
    holiday = get_object_or_404(Holiday, id=id)
    
    if request.method == 'POST':
        try:
            title = holiday.title
            holiday.delete()
            messages.success(request, f"Holiday '{title}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting holiday: {str(e)}")
    
    return redirect(reverse('managers:holidays_list'))


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def bulk_delete_holidays(request):
    from employe.models import Holiday
    
    if request.method == 'POST':
        holiday_ids = request.POST.getlist('holiday_ids')
        try:
            Holiday.objects.filter(id__in=holiday_ids).delete()
            messages.success(request, f"{len(holiday_ids)} holiday(s) deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting holidays: {str(e)}")
    
    return redirect(reverse('managers:holidays_list'))


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def employees_list(request):
    if is_founder(request.user):
        employes = list(
            Employe.objects.all().select_related(
                'user', 'manager', 'manager__user', 'founder', 'founder__user',
                'previous_manager', 'previous_manager__user',
            )
        )
        employees = build_founder_employee_table_rows(employes)
        context = {'employees': employees, 'is_founder_list': True}
    else:
        try:
            manager = Manager.objects.get(user=request.user)
            from common.utils import get_employees_under_manager
            employees = get_employees_under_manager(manager)
        except Manager.DoesNotExist:
            employees = Employe.objects.none()
        context = {'employees': employees, 'is_founder_list': False}

    return render(request, 'managers/employees_list.html', context)


@login_required(login_url='/managers/founder/login/')
@allow_founder
def all_leave_history(request):
    user_role = get_user_role(request.user)
    
    if user_role == 'founder':
        # Fetch all leave requests for all employees
        employee_leaves = LeaveRequest.objects.all().select_related('employee')
        # Fetch all leave requests for all managers
        manager_leaves = UnifiedLeaveRequest.objects.filter(
            requested_by_role='manager'
        ).select_related('manager__user')
    else:
        # Fallback for managers or others - should ideally be filtered too
        try:
            manager = Manager.objects.get(user=request.user)
            employee_leaves = LeaveRequest.objects.filter(employee__manager=manager).select_related('employee')
            manager_leaves = UnifiedLeaveRequest.objects.filter(
                manager=manager,
                requested_by_role='manager'
            ).select_related('manager__user')
        except Manager.DoesNotExist:
            employee_leaves = LeaveRequest.objects.none()
            manager_leaves = UnifiedLeaveRequest.objects.none()

    # Combine and sort all leave requests by creation date
    all_leaves = sorted(
        list(employee_leaves) + list(manager_leaves),
        key=lambda x: x.created_date,
        reverse=True
    )

    # RECALCULATE LEAVE DURATION FOR DISPLAY
    for leave in all_leaves:
        leave.leave_duration = leave.calculate_working_days()

    context = {
        'all_leaves': all_leaves,
    }
    return render(request, 'managers/all_leave_history.html', context)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def employee_leave_history(request):
    if is_founder(request.user):
        leave_requests = LeaveRequest.objects.all().select_related('employee').order_by('-created_date')
    else:
        try:
            manager = Manager.objects.get(user=request.user)
            from common.utils import get_employees_under_manager
            employees = get_employees_under_manager(manager)
            leave_requests = LeaveRequest.objects.filter(
                employee__in=employees
            ).order_by('-created_date')
        except Manager.DoesNotExist:
            leave_requests = LeaveRequest.objects.none()
    
    # Recalculate duration for display
    for leave in leave_requests:
        leave.leave_duration = leave.calculate_working_days()
    
    context = {
        'leave_history': leave_requests,
    }
    return render(request, 'managers/employee_leave_history.html', context)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def leave_summary(request):
    if is_founder(request.user):
        employees = Employe.objects.all()
        managers = Manager.objects.all()
    else:
        try:
            manager = Manager.objects.get(user=request.user)
            employees = Employe.objects.filter(manager=manager)
            managers = Manager.objects.filter(id=manager.id)
        except Manager.DoesNotExist:
            employees = Employe.objects.none()
            managers = Manager.objects.none()
    
    employee_summary = []
    for emp in employees:
        employee_summary.append({
            'employee': emp,
            'leave_balance': get_leave_balance_info(emp.user)
        })
    
    manager_summary = []
    for mng in managers:
        # Calculate remaining leaves for the manager
        total_annual_taken = UnifiedLeaveRequest.objects.filter(
            manager=mng,
            leave_type='AL',
            is_approved=True,
            is_withdrawn=False,
        ).aggregate(total=Sum('leave_duration'))['total'] or 0

        total_medical_taken = UnifiedLeaveRequest.objects.filter(
            manager=mng,
            leave_type='ML',
            is_approved=True,
            is_withdrawn=False,
        ).aggregate(total=Sum('leave_duration'))['total'] or 0

        manager_summary.append({
            'manager': mng,
            'annual_taken': total_annual_taken,
            'medical_taken': total_medical_taken,
            'annual_remaining': 18 - total_annual_taken,
            'medical_remaining': 14 - total_medical_taken,
        })

    context = {
        'employee_summary': employee_summary,
        'manager_summary': manager_summary,
    }
    return render(request, 'managers/leave_summary.html', context)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def employee_detail(request, id):
    employe = get_object_or_404(Employe, id=id)
    user = employe.user
    
    leave_requests = LeaveRequest.objects.filter(employee=user).order_by('-created_date')
    
    # Recalculate duration for display
    for leave in leave_requests:
        leave.leave_duration = leave.calculate_working_days()

    context = {
        'employe': employe,
        'user': user,
        'leave_requests': leave_requests,
    }
    return render(request, 'managers/employee_detail.html', context)


def manager_forget_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(Q(email=email) & (Q(is_manager=True) | Q(is_superuser=True)))
            
            # Rate limiting: Max 3 OTPs per hour
            one_hour_ago = timezone.now() - timedelta(hours=1)
            otp_count = OTP.objects.filter(user=user, created_at__gte=one_hour_ago).count()
            
            if otp_count >= 3:
                messages.error(request, "Maximum OTP limit reached (3 per hour). Please try again later.")
                return render(request, 'managers/forget_password.html')

            otp_code = str(random.randint(100000, 999999))
            otp, created = OTP.objects.update_or_create(
                user=user,
                defaults={
                    'otp': otp_code,
                    'expires_at': timezone.now() + timedelta(minutes=5)
                }
            )
            
            subject = "Password Reset OTP"
            message = f"Your OTP for password reset is: {otp_code}\nThis OTP is valid for 5 minutes."
            
            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
                request.session['reset_email'] = email
                messages.success(request, "OTP sent to your email!")
                return redirect(reverse('managers:reset_password'))
            except Exception as e:
                messages.error(request, f"Failed to send email. You may have reached your daily limit or the configuration is incorrect. Error: {str(e)}")
                return render(request, 'managers/forget_password.html')
            
        except User.DoesNotExist:
            messages.error(request, "No manager account found with this email.")
    
    return render(request, 'managers/forget_password.html')


def manager_resend_otp(request):
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect(reverse('managers:forget_password'))
    
    try:
        user = User.objects.get(email=email)
        
        # Rate limiting: Max 3 OTPs per hour
        one_hour_ago = timezone.now() - timedelta(hours=1)
        otp_count = OTP.objects.filter(user=user, created_at__gte=one_hour_ago).count()
        
        if otp_count >= 3:
            messages.error(request, "Maximum OTP limit reached (3 per hour). Please try again later.")
            return redirect(reverse('managers:reset_password'))

        otp_code = str(random.randint(100000, 999999))
        OTP.objects.update_or_create(
            user=user,
            defaults={
                'otp': otp_code,
                'expires_at': timezone.now() + timedelta(minutes=5)
            }
        )
        
        subject = "Password Reset OTP"
        message = f"Your OTP for password reset is: {otp_code}\nThis OTP is valid for 5 minutes."
        
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
            messages.success(request, "OTP resent to your email!")
        except Exception as e:
            messages.error(request, f"Failed to send email. Error: {str(e)}")
            
        return redirect(reverse('managers:reset_password'))
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect(reverse('managers:forget_password'))


def manager_reset_password(request):
    if request.method == 'POST':
        email = request.session.get('reset_email')
        otp_code = request.POST.get('otp')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'managers/reset_password.html')
        
        try:
            user = User.objects.get(email=email)
            otp = OTP.objects.get(user=user, otp=otp_code)
            
            if otp.is_expired():
                messages.error(request, "OTP has expired!")
                return render(request, 'managers/reset_password.html')
            
            user.set_password(new_password)
            user.save()
            
            otp.delete()
            
            if 'reset_email' in request.session:
                del request.session['reset_email']
            
            messages.success(request, "Password reset successfully! Please login.")
            return redirect(reverse('managers:login'))
            
        except (User.DoesNotExist, OTP.DoesNotExist):
            messages.error(request, "Invalid OTP!")
    
    return render(request, 'managers/reset_password.html')


@login_required(login_url='/managers/login')
@role_required('manager')
def view_profile(request):
    manager = get_object_or_404(Manager, user=request.user)
    
    try:
        address = AddressManager.objects.get(manager=manager)
    except AddressManager.DoesNotExist:
        address = None
        
    try:
        contact = EmergencyContactManager.objects.get(manager=manager)
    except EmergencyContactManager.DoesNotExist:
        contact = None
        
    try:
        benefits = BenefitsManager.objects.get(manager=manager)
    except BenefitsManager.DoesNotExist:
        benefits = None

    try:
        workschedule = WorkScheduleManager.objects.get(manager=manager)
    except WorkScheduleManager.DoesNotExist:
        workschedule = None

    context = {
        'manager': manager,
        'user': manager.user,
        'address': address,
        'contact': contact,
        'benefits': benefits,
        'workschedule': workschedule,
    }
    return render(request, 'managers/details.html', context)


@login_required(login_url='/managers/login')
@role_required('manager')
def edit_profile(request):
    manager = get_object_or_404(Manager, user=request.user)
    
    if request.method == 'POST':
        form = ManagerProfileForm(request.POST, request.FILES, instance=manager)
        if form.is_valid():
            # Update User model fields
            user = manager.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.phone_number = form.cleaned_data['phone_number']
            user.gender = form.cleaned_data['gender']
            user.date_of_birth = form.cleaned_data['date_of_birth']
            user.save()
            
            # Update Manager model fields (manager_id, designation, image)
            form.save()
            
            # Update or create related models
            AddressManager.objects.update_or_create(
                manager=manager,
                defaults={
                    'Permanent_address': form.cleaned_data['address_permanent_address'],
                    'city': form.cleaned_data['address_city'],
                    'country': form.cleaned_data['address_country'],
                    'pincode': form.cleaned_data['address_pincode'],
                }
            )
            
            EmergencyContactManager.objects.update_or_create(
                manager=manager,
                defaults={
                    'Permanent_address': form.cleaned_data['contact_permanent_address'],
                    'country': form.cleaned_data['contact_country'],
                    'city': form.cleaned_data['contact_city'],
                    'pincode': form.cleaned_data['contact_pincode'],
                }
            )
            
            BenefitsManager.objects.update_or_create(
                manager=manager,
                defaults={
                    'bank_name': form.cleaned_data.get('bank_name'),
                    'account_number': form.cleaned_data.get('bank_account_number'),
                    'branch_name': form.cleaned_data.get('bank_branch_name'),
                    'ifsc_code': form.cleaned_data.get('bank_ifsc_code'),
                }
            )
            
            WorkScheduleManager.objects.update_or_create(
                manager=manager,
                defaults={
                    'start_time': form.cleaned_data['work_start_time'],
                    'end_time': form.cleaned_data['work_end_time'],
                }
            )
            
            messages.success(request, "Profile updated successfully!")
            return redirect('managers:view_profile')
    else:
        form = ManagerProfileForm(instance=manager)
    
    context = {
        'manager': manager,
        'form': form,
    }
    return render(request, 'managers/edit_profile.html', context)

@login_required
def manager_employee_leave_detail(request, employee_id):
    employe = get_object_or_404(Employe, id=employee_id)
    sync_prorated_leave_if_needed(employe)
    
    # Fetch leave history for this employee
    leave_history = LeaveRequest.objects.filter(employee=employe).order_by('-created_date')
    
    # Get manager info for header
    try:
        manager = request.user.manager
    except:
        manager = None
        
    context = {
        'employe': employe,
        'manager': manager,
        'leave_history': leave_history,
        'notification_count': 0,
    }
    
    return render(request, 'managers/employee_leave_detail.html', context)

@login_required
def founder_employee_leave_detail(request, employee_id):
    employe = get_object_or_404(Employe, id=employee_id)
    sync_employee_profile_from_related(employe)
    sync_prorated_leave_if_needed(employe)

    try:
        manager = request.user.manager
    except Exception:
        manager = None

    leave_history = LeaveRequest.objects.filter(employee=employe).order_by('-created_date')
    profile_display = get_employee_display_profile(employe)

    context = {
        'employe': employe,
        'manager': manager,
        'leave_history': leave_history,
        'profile_display': profile_display,
        'notification_count': 0,
    }

    return render(request, 'managers/founder_employee_leave_detail.html', context)


@login_required(login_url='/managers/founder/login/')
@allow_founder
def founder_manager_leave_detail(request, manager_id):
    manager_obj = get_object_or_404(Manager, id=manager_id)
    sync_prorated_leave_if_needed(manager_obj)
    
    # Fetch leave history using UnifiedLeaveRequest
    manager_leave_requests = UnifiedLeaveRequest.objects.filter(
        manager=manager_obj,
        requested_by_role='manager'
    ).order_by('-created_date')
    
    # Recalculate duration for display
    for leave in manager_leave_requests:
        leave.leave_duration = leave.calculate_working_days()
    
    # Get founder info for header if needed
    try:
        founder = request.user.founder
    except:
        founder = None
    
    context = {
        'manager_obj': manager_obj,
        'founder': founder,
        'manager_leave_requests': manager_leave_requests,
        'notification_count': 0,
        'is_manager_view': True,
    }
    
    return render(request, 'managers/founder_manager_leave_detail.html', context)
