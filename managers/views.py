from django.shortcuts import render, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages 
from django.shortcuts import redirect
from django.http.response import HttpResponseRedirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
import traceback
from datetime import datetime, timedelta
import re

from common.decorators import allow_manager
from employe.models import *
from users.models import User
from managers.models import *

from django.utils import timezone
from datetime import timedelta
import smtplib
import ssl

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail, EmailMessage
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.contrib.auth.password_validation import validate_password
from users.models import User
from users.models import OTP 
import random
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.validators import validate_email
import secrets
import logging

logger = logging.getLogger(__name__)

# Google Calendar integration
from .google_calendar_service import get_google_calendar_service
from .forms import UnifiedLeaveRequestForm, AddEmployeeForm
from common.decorators import role_required, allow_founder
from common.utils import get_user_role, is_founder, is_manager, get_user_profile, generate_manager_id, calculate_leave_days

logger = logging.getLogger(__name__)

# ==================== EMAIL FUNCTIONS ====================

def send_leave_notification(request, leave, email_type, recipient_email, manager_name=None):
    """
    Generic function to send leave notifications.
    - `leave`: The leave request object (LeaveRequest or UnifiedLeaveRequest).
    - `email_type`: 'new_request', 'approved', 'rejected', or 'submission_confirmation'.
    - `recipient_email`: The email address of the recipient.
    - `manager_name`: The name of the manager (for notifications to managers).
    """
    
    if isinstance(leave, LeaveRequest):
        requester_profile = get_object_or_404(Employe, user=leave.employee)
        requester_name = leave.employee.get_full_name()
        leave_model_name = 'LeaveRequest'
    elif isinstance(leave, UnifiedLeaveRequest):
        requester_profile = leave.manager
        requester_name = leave.manager.user.get_full_name()
        leave_model_name = 'UnifiedLeaveRequest'
    else:
        logger.error(f"Unknown leave model type: {type(leave)}")
        return

    if email_type == 'new_request':
        subject = f"New Leave Request from {requester_name}"
    elif email_type == 'approved':
        subject = "Your Leave Request has been Approved"
    elif email_type == 'rejected':
        subject = "Your Leave Request has been Rejected"
    elif email_type == 'submission_confirmation':
        subject = "Leave Request Submitted Successfully"
    else:
        subject = "Leave Request Update"

    if email_type == 'new_request':
        if leave_model_name == 'LeaveRequest':
            # FIX: Corrected reverse lookup from 'leave_requests' to 'leavelist'
            review_path = reverse('managers:leavelist')
        else:
            review_path = reverse('managers:manager_leave_requests_list')
        review_url = request.build_absolute_uri(review_path)
    else:
        review_url = None

    html_content = render_to_string('emails/leave_notification.html', {
        'leave': leave,
        'employee': requester_profile,
        'email_type': email_type,
        'status': leave.status,
        'manager_name': manager_name,
        'review_url': review_url,
    })

    try:
        email = EmailMessage(
            subject,
            body=html_content,
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient_email]
        )
        email.content_subtype = 'html'
        email.send()
        logger.info(f"Leave notification '{email_type}' sent to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")


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


@login_required(login_url='/managers/login')
@allow_founder
def founder_dashboard(request):
    founders = Founder.objects.all()
    managers = Manager.objects.all()
    employes = Employe.objects.all()
    holidays = Holiday.objects.all()

    manager_leave_requests = UnifiedLeaveRequest.objects.filter(
        requested_by_role='manager',
        is_approved=False,
        is_rejected=False
    ).select_related('manager__user').order_by('-created_date')[:5]

    employee_leave_requests = LeaveRequest.objects.filter(
        status='Pending'
    ).select_related('employee').order_by('-created_date')[:5]

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
            'approved_by': leave.approved_by,
            'approval_date': leave.approval_date,
        })

    recent_employee_leaves = LeaveRequest.objects.filter(
        status='Approved'
    ).select_related('employee').order_by('-id')[:5]

    employee_users = [leave.employee for leave in recent_employee_leaves]
    employe_objects = Employe.objects.filter(user__in=employee_users).select_related('user')
    employe_map = {employe.user.id: employe for employe in employe_objects}

    for leave in recent_employee_leaves:
        employee_profile = employe_map.get(leave.employee.id)
        recent_approved_leaves.append({
            'requester_name': f"{leave.employee.first_name} {leave.employee.last_name}",
            'requested_by_role': 'employee',
            'employee': employee_profile,
            'subject': leave.subject,
            'start_date': leave.start_date,
            'end_date': leave.end_date,
            'approved_by': None,
            'approval_date': leave.approval_date,
        })

    recent_approved_leaves = recent_approved_leaves[:5]

    context = {
        'founders': founders,
        'managers': managers,
        'employees': employes,
        'holidays': holidays,
        'f_count': founders.count(),
        'm_count': managers.count(),
        'e_count': employes.count(),
        'h_count': holidays.count(),
        'manager_leave_requests': manager_leave_requests,
        'employee_leave_requests': employee_leave_requests,
        'recent_approved_leaves': recent_approved_leaves,
        'pending_manager_leaves': manager_leave_requests.count(),
        'pending_employee_leaves': employee_leave_requests.count(),
    }

    return render(request, 'managers/founder_dashboard.html', context)


@login_required(login_url='/managers/login')
@role_required('manager')
def manager_dashboard(request):
    try:
        manager = Manager.objects.get(user=request.user)
    except Manager.DoesNotExist:
        messages.error(request, "Manager profile not found.")
        return redirect(reverse('managers:login'))

    from common.utils import get_employees_under_manager
    employees = get_employees_under_manager(manager)

    pending_employee_requests = LeaveRequest.objects.filter(
        employee__in=[emp.user for emp in employees],
        status='Pending'
    ).order_by('-created_date')

    manager_leave_requests = UnifiedLeaveRequest.objects.filter(
        manager=manager,
        requested_by_role='manager'
    ).order_by('-created_date')[:5]

    recent_approved_employee_leaves = LeaveRequest.objects.filter(
        employee__in=[emp.user for emp in employees],
        status='Approved'
    ).order_by('-created_date')[:5]
    
    leave_history = LeaveRequest.objects.filter(employee__in=[emp.user for emp in employees]).order_by('-created_date')

    context = {
        'manager': manager,
        'employees': employees,
        'employee_count': employees.count(),
        'pending_employee_requests': pending_employee_requests,
        'pending_count': pending_employee_requests.count(),
        'manager_leave_requests': manager_leave_requests,
        'recent_approved_employee_leaves': recent_approved_employee_leaves,
        'leave_history': leave_history,
        'leave_requests': pending_employee_requests,
        'manager_leaves': manager_leave_requests,
        'notification_count': pending_employee_requests.count(),
    }

    return render(request, 'managers/manager_dashboard.html', context)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def approve_employee_leave(request, leave_id):
    leave_request = get_object_or_404(LeaveRequest, id=leave_id)
    employee_profile = get_object_or_404(Employe, user=leave_request.employee)

    if request.method == 'POST':
        if not (request.user.is_superuser or employee_profile.manager.user == request.user):
            messages.error(request, "You do not have permission to approve this leave request.")
            return redirect('managers:manager_dashboard')

        leave_days = calculate_leave_days(leave_request.start_date, leave_request.end_date)

        if leave_request.leave_type == 'ML':
            if employee_profile.available_medical_leaves >= leave_days:
                employee_profile.medical_leaves_taken += leave_days
                employee_profile.available_medical_leaves -= leave_days
            else:
                messages.error(request, "Not enough medical leave balance.")
                return redirect('managers:leavelist')
        elif leave_request.leave_type == 'AL':
            if employee_profile.available_leaves >= leave_days:
                employee_profile.leaves_taken += leave_days
                employee_profile.available_leaves -= leave_days
            else:
                messages.error(request, "Not enough annual leave balance.")
                return redirect('managers:leavelist')

        employee_profile.save()

        leave_request.status = 'Approved'
        leave_request.is_approved = True
        leave_request.approval_date = timezone.now()
        leave_request.leave_duration = leave_days
        leave_request.save()

        send_leave_notification(request, leave_request, 'approved', leave_request.employee.email)

        messages.success(request, f"Leave request for {leave_request.employee.get_full_name()} approved.")
        return redirect('managers:leavelist')

    return redirect('managers:leavelist')


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def reject_employee_leave(request, leave_id):
    leave_request = get_object_or_404(LeaveRequest, id=leave_id)
    employee_profile = get_object_or_404(Employe, user=leave_request.employee)

    if request.method == 'POST':
        if not (request.user.is_superuser or employee_profile.manager.user == request.user):
            messages.error(request, "You do not have permission to reject this leave request.")
            return redirect('managers:manager_dashboard')

        leave_request.status = 'Rejected'
        leave_request.is_rejected = True
        leave_request.rejection_date = timezone.now()
        leave_request.save()

        send_leave_notification(request, leave_request, 'rejected', leave_request.employee.email)

        messages.success(request, f"Leave request for {leave_request.employee.get_full_name()} rejected.")
        return redirect('managers:leavelist')

    return redirect('managers:leavelist')


@login_required(login_url='/managers/login')
@role_required('manager')
def manager_apply_leave(request):
    if request.method == 'POST':
        form = UnifiedLeaveRequestForm(request.POST, request.FILES)
        if form.is_valid():
            leave_request = form.save(commit=False)

            try:
                manager = Manager.objects.get(user=request.user)
                leave_request.manager = manager
                leave_request.requested_by_role = 'manager'
                leave_request.save()

                founders = Founder.objects.all()
                for founder in founders:
                    send_leave_notification(request, leave_request, 'new_request', founder.user.email, manager_name=founder.user.get_full_name())
                
                send_leave_notification(request, leave_request, 'submission_confirmation', request.user.email)

                messages.success(request, "Leave request submitted successfully!")
                return redirect(reverse("managers:manager_leave_history"))

            except Manager.DoesNotExist:
                messages.error(request, "Manager profile not found.")

    else:
        form = UnifiedLeaveRequestForm()

    return render(request, 'managers/apply_leave.html', {'form': form})


@login_required(login_url='/managers/login')
@allow_founder
def approve_manager_leave(request, id):
    leave_request = get_object_or_404(UnifiedLeaveRequest, id=id, requested_by_role='manager')
    manager = leave_request.manager

    actual_leave_days = calculate_leave_days(leave_request.start_date, leave_request.end_date)

    leave_request.is_approved = True
    leave_request.approval_date = timezone.now()
    leave_request.approved_by = request.user
    leave_request.leave_duration = actual_leave_days
    leave_request.status = 'approved'
    leave_request.save()

    if leave_request.leave_type == 'ML':
        manager.medical_leaves_taken += actual_leave_days
        manager.available_medical_leaves -= actual_leave_days
    elif leave_request.leave_type == 'AL':
        manager.leaves_taken += actual_leave_days
        manager.available_leaves -= actual_leave_days

    manager.save()

    send_leave_notification(request, leave_request, 'approved', manager.user.email)

    messages.success(request, f"Manager leave request approved successfully for {actual_leave_days} days.")
    return redirect(reverse("managers:founder_dashboard"))


@login_required(login_url='/managers/login')
@allow_founder
def reject_manager_leave(request, id):
    leave_request = get_object_or_404(UnifiedLeaveRequest, id=id, requested_by_role='manager')

    leave_request.is_rejected = True
    leave_request.rejection_date = timezone.now()
    leave_request.rejected_by = request.user
    leave_request.status = 'rejected'
    leave_request.save()

    send_leave_notification(request, leave_request, 'rejected', leave_request.manager.user.email)

    messages.success(request, "Manager leave request rejected successfully.")
    return redirect(reverse("managers:founder_dashboard"))


@login_required(login_url='/managers/login')
@role_required('manager')
def manager_leave_history(request):
    try:
        manager = Manager.objects.get(user=request.user)
        unified_requests = UnifiedLeaveRequest.objects.filter(
            manager=manager,
            requested_by_role='manager'
        ).order_by('-created_date')

        for leave_request in unified_requests:
            leave_request.calculated_duration = calculate_leave_days(leave_request.start_date, leave_request.end_date)

        context = {
            'unified_requests': unified_requests,
            'manager': manager
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
        is_rejected=False
    ).order_by('-created_date')

    for leave_request in pending_requests:
        leave_request.calculated_duration = calculate_leave_days(leave_request.start_date, leave_request.end_date)

    context = {
        'leave_requests': pending_requests,
        'is_founder': True
    }
    return render(request, 'managers/manager_leave_requests.html', context)


@login_required(login_url='/managers/login')
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
    employees = get_employees_under_manager(manager)

    pending_employee_requests = LeaveRequest.objects.filter(
        employee__in=[emp.user for emp in employees],
        status='Pending'
    ).order_by('-created_date')

    context = {
        'leave_requests': pending_employee_requests,
        'manager': manager,
        'notification_count': pending_employee_requests.count(),
    }
    return render(request, 'managers/leave_requests.html', context)


def login(request):
    context = {"title": "Login"}
    
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password")

        if email and password:
            user = authenticate(request, email=email, password=password)
            
            if user:
                if user.is_superuser or user.is_manager:
                    auth_login(request, user)
                    user.is_manager = True
                    user.save()
                    manager, created = Manager.objects.get_or_create(user=user)
                    return HttpResponseRedirect(reverse("managers:index"))
                else:
                    messages.error(request, "Access restricted")
            else:
                messages.error(request, "Invalid email or password")
        else:
            messages.error(request, "Email and password are required")

    return render(request, "managers/login.html", context)


def logout(request):
    auth_logout(request)
    return HttpResponseRedirect(reverse("managers:login"))


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def viewlist(request, id):
    leave_request = get_object_or_404(LeaveRequest, id=id)
    employe = get_object_or_404(Employe, user=leave_request.employee)
    
    context = {
        'leave_request': leave_request,
        'employe': employe,
        'user': leave_request.employee,
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


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def add_employe(request):
    if request.method == 'POST':
        form = AddEmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = User.objects.create_user(
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    phone_number=form.cleaned_data.get('phone_number', ''),
                    gender=form.cleaned_data.get('gender', ''),
                    is_employee=True
                )
                
                manager = None
                if is_manager(request.user):
                    manager = Manager.objects.get(user=request.user)
                
                employe = Employe.objects.create(
                    user=user,
                    manager=manager,
                    department=form.cleaned_data.get('department', ''),
                    designation=form.cleaned_data.get('designation', ''),
                    date_of_joining=form.cleaned_data.get('date_of_joining'),
                    employment_Type=form.cleaned_data.get('employment_Type', ''),
                    work_location=form.cleaned_data.get('work_location', ''),
                    image=form.cleaned_data.get('image'),
                )
                
                messages.success(request, f"Employee {user.get_full_name()} added successfully!")
                return redirect(reverse('managers:employees_list'))
                
            except Exception as e:
                messages.error(request, f"Error creating employee: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = AddEmployeeForm()
    
    return render(request, 'managers/add_employe.html', {'form': form})


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def edit_employe(request, id):
    employe = get_object_or_404(Employe, id=id)
    user = employe.user
    
    if request.method == 'POST':
        try:
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.phone_number = request.POST.get('phone_number', user.phone_number)
            
            date_of_birth_str = request.POST.get('date_of_birth')
            if date_of_birth_str:
                user.date_of_birth = date_of_birth_str
                
            user.save()
            
            employe.department = request.POST.get('department', employe.department)
            employe.designation = request.POST.get('designation', employe.designation)
            employe.work_location = request.POST.get('work_location', employe.work_location)
            
            if request.FILES.get('image'):
                employe.image = request.FILES['image']
            
            employe.save()
            
            messages.success(request, f"Employee {user.get_full_name()} updated successfully!")
            return redirect(reverse('managers:employees_list'))
            
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
    employe = get_object_or_404(Employe, id=id)
    user = employe.user
    
    context = {
        'employe': employe,
        'user': user,
    }
    return render(request, 'managers/details.html', context)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def delete_employee(request, id):
    employe = get_object_or_404(Employe, id=id)
    user = employe.user
    
    if request.method == 'POST':
        try:
            user_name = user.get_full_name()
            user.delete()
            messages.success(request, f"Employee {user_name} deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting employee: {str(e)}")
    
    return redirect(reverse('managers:employees_list'))


@login_required(login_url='/managers/login')
@allow_founder
def add_manager(request):
    if request.method == 'POST':
        try:
            user = User.objects.create_user(
                email=request.POST['email'],
                password=request.POST['password'],
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name'],
                phone_number=request.POST.get('phone_number', ''),
                gender=request.POST.get('gender', ''),
                is_manager=True
            )
            
            manager_id = generate_manager_id()
            
            manager = Manager.objects.create(
                user=user,
                manager_id=manager_id,
                department=request.POST.get('department', ''),
                designation=request.POST.get('designation', ''),
                date_of_joining=request.POST.get('date_of_joining'),
                employment_Type=request.POST.get('employment_Type', ''),
                work_location=request.POST.get('work_location', ''),
            )
            
            if request.FILES.get('image'):
                manager.image = request.FILES['image']
                manager.save()
            
            messages.success(request, f"Manager {user.get_full_name()} added successfully!")
            return redirect(reverse('managers:founder_dashboard'))
            
        except Exception as e:
            messages.error(request, f"Error creating manager: {str(e)}")
    
    return render(request, 'managers/add_manager.html')


@login_required(login_url='/managers/login')
@allow_founder
def delete_manager(request, id):
    manager = get_object_or_404(Manager, id=id)
    user = manager.user
    
    if request.method == 'POST':
        try:
            user_name = user.get_full_name()
            user.delete()
            messages.success(request, f"Manager {user_name} deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting manager: {str(e)}")
    
    return redirect(reverse('managers:founder_dashboard'))


@login_required(login_url='/managers/login')
@allow_founder
def founder_add(request):
    if request.method == 'POST':
        try:
            user = User.objects.create_user(
                email=request.POST['email'],
                password=request.POST['password'],
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name'],
                phone_number=request.POST.get('phone_number', ''),
                gender=request.POST.get('gender', ''),
                is_superuser=True,
                is_staff=True
            )
            
            founder = Founder.objects.create(
                user=user,
                department=request.POST.get('department', ''),
                designation=request.POST.get('designation', ''),
                date_of_joining=request.POST.get('date_of_joining'),
                employment_Type=request.POST.get('employment_Type', ''),
                work_location=request.POST.get('work_location', ''),
            )
            
            if request.FILES.get('image'):
                founder.image = request.FILES['image']
                founder.save()
            
            messages.success(request, f"Founder {user.get_full_name()} added successfully!")
            return redirect(reverse('managers:founder_dashboard'))
            
        except Exception as e:
            messages.error(request, f"Error creating founder: {str(e)}")
    
    return render(request, 'managers/add_founder.html')


@login_required(login_url='/managers/login')
@allow_founder
def delete_founder(request, id):
    founder = get_object_or_404(Founder, id=id)
    user = founder.user
    
    if request.method == 'POST':
        try:
            user_name = user.get_full_name()
            user.delete()
            messages.success(request, f"Founder {user_name} deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting founder: {str(e)}")
    
    return redirect(reverse('managers:founder_dashboard'))


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
        employees = Employe.objects.all().select_related('user', 'manager')
    else:
        try:
            manager = Manager.objects.get(user=request.user)
            from common.utils import get_employees_under_manager
            employees = get_employees_under_manager(manager)
        except Manager.DoesNotExist:
            employees = Employe.objects.none()
    
    context = {
        'employees': employees,
    }
    return render(request, 'managers/employees_list.html', context)


@login_required(login_url='/managers/login')
@allow_founder
def all_leave_history(request):
    employee_leaves = LeaveRequest.objects.all().select_related('employee').order_by('-created_date')
    
    manager_leaves = UnifiedLeaveRequest.objects.filter(
        requested_by_role='manager'
    ).select_related('manager__user').order_by('-created_date')
    
    context = {
        'employee_leaves': employee_leaves,
        'manager_leaves': manager_leaves,
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
                employee__in=[emp.user for emp in employees]
            ).order_by('-created_date')
        except Manager.DoesNotExist:
            leave_requests = LeaveRequest.objects.none()
    
    context = {
        'leave_requests': leave_requests,
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
            from common.utils import get_employees_under_manager
            employees = get_employees_under_manager(manager)
            managers = Manager.objects.none()
        except Manager.DoesNotExist:
            employees = Employe.objects.none()
            managers = Manager.objects.none()
    
    context = {
        'employees': employees,
        'managers': managers,
    }
    return render(request, 'managers/leave_summary.html', context)


@login_required(login_url='/managers/login')
@role_required('manager', 'founder')
def employee_detail(request, id):
    employe = get_object_or_404(Employe, id=id)
    user = employe.user
    
    leave_requests = LeaveRequest.objects.filter(employee=user).order_by('-created_date')
    
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
            user = User.objects.get(email=email, is_manager=True)
            
            otp_code = str(random.randint(100000, 999999))
            otp, created = OTP.objects.get_or_create(user=user)
            otp.otp = otp_code
            otp.save()
            
            subject = "Password Reset OTP"
            message = f"Your OTP for password reset is: {otp_code}\nThis OTP is valid for 10 minutes."
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
            
            request.session['reset_email'] = email
            messages.success(request, "OTP sent to your email!")
            return redirect(reverse('managers:reset_password'))
            
        except User.DoesNotExist:
            messages.error(request, "No manager account found with this email.")
    
    return render(request, 'managers/forget_password.html')


def manager_reset_password(request):
    if request.method == 'POST':
        email = request.session.get('reset_email')
        otp_code = request.POST.get('otp')
        new_password = request.POST.get('password')
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