from django.shortcuts import render,  reverse, get_object_or_404
from django.shortcuts import HttpResponse

from django.http.response import HttpResponseRedirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required

from common.decorators import allow_employee, role_required
from common.utils import get_user_profile, get_leave_balance_info
from employe.models import *
from employe.models import LeaveRequest
from managers.models import *
from users.models import *
from datetime import datetime
from managers.views import send_leave_notification


from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
import random
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from django.conf import settings
import smtplib
import ssl

from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import secrets
from django.contrib.auth.hashers import make_password

from users.models import OTP


@login_required(login_url='/login')
@allow_employee
def details(request):
    user = request.user
    employe = get_object_or_404(Employe, user=user)
    contact, _ = EmergencyContact.objects.get_or_create(employe=employe)
    address, _ = Address.objects.get_or_create(employe=employe)
    background, _ = Background.objects.get_or_create(employe=employe)
    benefits, _ = Benefits.objects.get_or_create(employe=employe)
    identification, _ = Identification.objects.get_or_create(employe=employe)
    schedule, _ = WorkSchedule.objects.get_or_create(employe=employe)
    holidays = Holiday.objects.all()
    leave_history = LeaveRequest.objects.filter(employee=employe).order_by('-created_date')
    leave_balance_info = get_leave_balance_info(request.user)

    context ={
        'employe': employe,
        'user': user,
        'contact': contact,
        'address': address,
        'background': background,
        'benefits': benefits,
        'identification': identification,
        'schedule': schedule,
        'holidays':holidays,
        'leave_history': leave_history,
        'leave_balance_info': leave_balance_info
    }

    return render(request, "employe/details.html", context=context)


@login_required(login_url='/login')
@allow_employee
def employee_dashboard(request):
    """Dashboard specifically for employees"""
    try:
        employee = Employe.objects.get(user=request.user)
    except Employe.DoesNotExist:
        messages.error(request, "Employee profile not found.")
        return redirect(reverse('employe:login'))

    leave_requests = LeaveRequest.objects.filter(
        employee=employee
    ).order_by('-created_date')[:5]

    pending_requests = LeaveRequest.objects.filter(
        employee=employee,
        status='Pending'
    ).count()

    for leave_request in leave_requests:
        if leave_request.start_date and leave_request.end_date:
            leave_request.calculated_duration = (leave_request.end_date - leave_request.start_date).days + 1
        else:
            leave_request.calculated_duration = 0

    leave_balance_info = get_leave_balance_info(request.user)

    context = {
        'employee': employee,
        'leave_requests': leave_requests,
        'pending_requests': pending_requests,
        'manager': employee.manager,
        'leave_balance_info': leave_balance_info,
    }

    return render(request, 'employe/employee_dashboard.html', context)


@login_required(login_url='/login')
@allow_employee
def apply_leave(request):
    user = request.user
    try:
        employe = Employe.objects.get(user=user)
    except Employe.DoesNotExist:
        messages.error(request, "Employee profile not found.")
        return redirect('employe:login')

    if request.method == 'POST':
        subject = request.POST.get('subject')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        leave_type = request.POST.get('leave_type')
        description = request.POST.get('description')
        file = request.FILES.get('file')

        if not all([subject, start_date_str, end_date_str, leave_type, description]):
            messages.error(request, "❌ All fields except file are required.")
            return render(request, "employe/leaveform.html", {
                'employe': employe,
                'leave_balance_info': get_leave_balance_info(request.user)
            })

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            if start_date > end_date:
                messages.error(request, "❌ Start date cannot be after end date.")
                return render(request, "employe/leaveform.html", {
                    'employe': employe,
                    'leave_balance_info': get_leave_balance_info(request.user)
                })

            leave_request = LeaveRequest.objects.create(
                subject=subject,
                leave_type=leave_type,
                description=description,
                file=file,
                employee=employe,
                start_date=start_date,
                end_date=end_date,
                status='Pending'
            )

            try:
                if employe.manager and employe.manager.user.email:
                    send_leave_notification(request, leave_request, 'new_request', employe.manager.user.email, manager_name=employe.manager.user.get_full_name(), cc_founder=True)
                
                send_leave_notification(request, leave_request, 'submission_confirmation', user.email)
                
                messages.success(request, "✅ Leave request submitted successfully. Notifications have been sent.")
            except Exception as e:
                messages.error(request, f"⚠️ Leave request saved, but failed to send email notifications. Error: {str(e)}")

            return HttpResponseRedirect(reverse("employe:leavelist"))

        except ValueError as e:
            messages.error(request, f"❌ Invalid date format: {e}")
            return render(request, "employe/leaveform.html", {'employe': employe})
        except Exception as e:
            messages.error(request, f"❌ Error creating leave request: {e}")
            return render(request, "employe/leaveform.html", {
                'employe': employe,
                'leave_balance_info': get_leave_balance_info(request.user)
            })

    return render(request, "employe/leaveform.html", {
        'employe': employe,
        'leave_balance_info': get_leave_balance_info(request.user)
    })

@login_required(login_url='/login')
@allow_employee
def leaveform(request):
    return apply_leave(request)


def logout(request):
    auth_logout(request)
    return HttpResponseRedirect(reverse("employe:login"))


from common.utils import is_employee
from .models import Employe

def login(request):
    # Consume all existing messages so they don't appear on the login page
    storage = messages.get_messages(request)
    for _ in storage:
        pass

    if request.method == "GET":
        return render(request, "employe/login.html", {"title": "Login", "messages": []})

    if request.method == 'POST':
        employe_id = request.POST.get("employe_id")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if email and password and employe_id:
            user = authenticate(request, email=email, password=password)
            if user is not None:
                try:
                    employee_profile = Employe.objects.get(user=user)
                    if employee_profile.employe_id != employe_id:
                        messages.error(request, "Invalid Employee ID for this account.")
                        return render(request, "employe/login.html", {"title": "Login", "messages": messages.get_messages(request)})
                    
                    auth_login(request, user)
                    return HttpResponseRedirect(reverse("employe:details"))
                except Employe.DoesNotExist:
                    messages.error(request, "Employee profile not found.")
                    return render(request, "employe/login.html", {"title": "Login", "messages": messages.get_messages(request)})
            else:
                messages.error(request, "Invalid credentials, please check your email and password.")
                return render(request, "employe/login.html", {"title": "Login", "messages": messages.get_messages(request)})
        
        messages.error(request, "Employee ID, Email and password are required.")
        return render(request, "employe/login.html", {"title": "Login", "messages": messages.get_messages(request)})
    
    return render(request, "employe/login.html", {"title": "Login", "messages": messages.get_messages(request)})


@login_required(login_url='/login')
@allow_employee
def leavelist(request):
    try:
        employee = Employe.objects.get(user=request.user)
    except Employe.DoesNotExist:
        messages.error(request, "Employee profile not found.")
        return redirect(reverse('employe:login'))

    instances = LeaveRequest.objects.filter(employee=employee).order_by('-created_date')

    for instance in instances:
        if instance.start_date and instance.end_date:
            instance.leave_duration = (instance.end_date - instance.start_date).days + 1
        else:
            instance.leave_duration = 0

    # Add employe to context
    return render(request, "employe/leavelist.html", {
        'instances': instances,
        'employe': employee  # Added this line
    })


@login_required(login_url='/login')
@allow_employee
def viewlist(request, id):
    try:
        current_employee = Employe.objects.get(user=request.user)
    except Employe.DoesNotExist:
        messages.error(request, "Employee profile not found.")
        return redirect(reverse('employe:leavelist'))

    try:
        leave_request = LeaveRequest.objects.get(id=id, employee=current_employee)
    except LeaveRequest.DoesNotExist:
        messages.error(request, "Leave request not found or access denied.")
        return redirect(reverse('employe:leavelist'))

    try:
        employee = leave_request.employee
        user = employee.user
    except Employe.DoesNotExist:
        messages.error(request, "Employee profile not found for this leave request.")
        return redirect(reverse('employe:leavelist'))

    return render(request, 'employe/viewlist.html', {
        'user': user,
        'employe': employee,
        'leave_request': leave_request,
    })


@login_required(login_url='/login')
@allow_employee
def cancel_leave(request, id):
    try:
        current_employee = Employe.objects.get(user=request.user)
    except Employe.DoesNotExist:
        messages.error(request, "Employee profile not found.")
        return redirect(reverse('employe:leavelist'))

    try:
        leave_request = LeaveRequest.objects.get(id=id, employee=current_employee)
    except LeaveRequest.DoesNotExist:
        messages.error(request, "Leave request not found or access denied.")
        return redirect(reverse('employe:leavelist'))

    if leave_request.status != 'Pending':
        messages.error(request, f"Cannot cancel a leave request that is already {leave_request.status}.")
        return redirect(reverse('employe:leavelist'))

    leave_request.status = 'Cancelled'
    leave_request.is_cancelled = True
    leave_request.cancellation_date = timezone.now().date()
    leave_request.save()

    # Send notifications
    try:
        from managers.views import send_leave_notification
        # Notify manager
        if current_employee.manager:
            manager_email = current_employee.manager.user.email
            manager_name = current_employee.manager.user.get_full_name()
            send_leave_notification(request, leave_request, 'cancelled', manager_email, manager_name=manager_name, cc_founder=True)
        else:
            # If no manager, notify founder directly
            send_leave_notification(request, leave_request, 'cancelled', None, cc_founder=True)
            
        messages.success(request, "Leave request cancelled successfully!")
    except Exception as e:
        messages.warning(request, f"Leave cancelled, but failed to send notifications: {str(e)}")

    return redirect(reverse('employe:leavelist'))

def get_int_or_none(value):
    try:
        return int(value) if value.strip() else None
    except (ValueError, TypeError):
        return None

def get_float_or_none(value):
    try:
        return float(value) if value.strip() else 0
    except (ValueError, TypeError):
        return 0

def get_time_or_none(value):
    try:
        return datetime.strptime(value.strip(), "%H:%M").time() if value.strip() else None
    except (ValueError, TypeError):
        return None

@login_required(login_url='/login')
@allow_employee
def edit_employe(request, id):
    employe = get_object_or_404(Employe, id=id)
    user = employe.user
    contact, _ = EmergencyContact.objects.get_or_create(employe=employe)
    address, _ = Address.objects.get_or_create(employe=employe)
    background, _ = Background.objects.get_or_create(employe=employe)
    benefits, _ = Benefits.objects.get_or_create(employe=employe)
    identification, _ = Identification.objects.get_or_create(employe=employe)
    schedule, _ = WorkSchedule.objects.get_or_create(employe=employe)

    if request.method == 'POST':
        # User details
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone_number = request.POST.get('phone_number')
        date_of_birth = request.POST.get('date_of_birth', '').strip()
        if date_of_birth:
            try:
                user.date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
        else:
            user.date_of_birth = None
        user.gender = request.POST.get('gender')
        user.save()

        # Emergency Contact
        contact.contact_name = request.POST.get('contact_name')
        contact.contact_number = request.POST.get('contact_number')
        contact.relationship = request.POST.get('relationship')
        contact.country = request.POST.get('emergency_country')
        contact.city = request.POST.get('emergency_city')
        contact.pincode = request.POST.get('emergency_pincode')
        contact.save()

        # Employee details
        employe.department = request.POST.get('department')
        employe.designation = request.POST.get('designation')
        # Don't allow employees to change their own ID
        date_of_joining = request.POST.get('date_of_joining', '').strip()
        if date_of_joining:
            try:
                employe.date_of_joining = datetime.strptime(date_of_joining, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
        else:
            employe.date_of_joining = None
        employe.employment_Type = request.POST.get('employment_Type')
        employe.reporting_manager = request.POST.get('reporting_manager')
        employe.work_location = request.POST.get('work_location')
        employe.employe_status = request.POST.get('employe_status')
        employe.save()

        # Address
        address.permanent_address = request.POST.get('permanent_address')
        address.country = request.POST.get('country')
        address.city = request.POST.get('city')
        address.pincode = request.POST.get('pincode')
        address.save()

        # Benefits
        benefits.salary_details = request.POST.get('salary_details')
        benefits.bank_name = request.POST.get('bank_name')
        benefits.account_number = get_int_or_none(request.POST.get('account_number'))
        benefits.branch_name = request.POST.get('branch_name')
        benefits.ifsc_code = request.POST.get('ifsc_code')
        benefits.pancard = request.POST.get('pancard')
        benefits.pf_fund = get_float_or_none(request.POST.get('pf_fund'))
        benefits.state_insurance_number = request.POST.get('state_insurance_number')
        benefits.save()

        # Background
        background.educational_qualifications = request.POST.get('educational_qualifications')
        background.previous_details = request.POST.get('previous_details')
        background.save()

        # Identification
        identification.work_authorization = request.POST.get('work_authorization')
        identification.save()

        # Work Schedule
        schedule.start_time = get_time_or_none(request.POST.get('start_time'))
        schedule.end_time = get_time_or_none(request.POST.get('end_time'))
        schedule.save()

        messages.success(request, "Details updated successfully!")
        return HttpResponseRedirect(reverse("employe:details"))

    context = {
        'employe': employe,
        'user': user,
        'contact': contact,
        'address': address,
        'background': background,
        'benefits': benefits,
        'identification': identification,
        'schedule': schedule,
    }

    return render(request, "employe/edit_employe.html", context=context)

User = get_user_model()


def forget_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            
            otp = secrets.randbelow(899999) + 100000
            expires_at = timezone.now() + timedelta(minutes=10)
            
            OTP.objects.create(user=user, otp=otp, expires_at=expires_at)
            
            request.session['reset_user_email'] = email
            
            try:
                send_mail(
                    'Reset Password OTP',
                    f'Your OTP for resetting the password is {otp}',
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )
                return HttpResponseRedirect(reverse('employe:reset_password'))
            except Exception as e:
                context = {
                    "title": "Forget Password",
                    "message": f"Failed to send OTP. Error: {str(e)}",
                }
                return render(request, "employe/forget_password.html", context)
        
        else:
            context = {
                "title": "Forget Password",
                "message": "Invalid email address",
            }
            return render(request, "employe/forget_password.html", context)
    
    context = {"title": "Forget Password"}
    return render(request, "employe/forget_password.html", context)


def resend_otp(request):
    email = request.session.get('reset_user_email')
    if not email:
        messages.error(request, "Session expired. Please restart the password reset process.")
        return redirect('employe:forget_password')
    
    try:
        user = User.objects.get(email=email)
        otp = secrets.randbelow(899999) + 100000
        expires_at = timezone.now() + timedelta(minutes=10)
        
        OTP.objects.create(user=user, otp=otp, expires_at=expires_at)
        
        send_mail(
            'Reset Password OTP',
            f'Your OTP for resetting the password is {otp}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
        messages.success(request, "OTP resent to your email!")
    except Exception as e:
        messages.error(request, f"Failed to resend OTP: {str(e)}")
        
    return redirect('employe:reset_password')


def reset_password(request):
    context = {"title": "Reset Password"}
    
    if request.method == "POST":
        otp = request.POST.get("otp")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        
        email = request.session.get('reset_user_email')
        if not email:
            messages.error(request, "Session expired. Please restart the password reset process.")
            return redirect('employe:forget_password')
        
        try:
            user = User.objects.get(email=email)
            
            otp_obj = OTP.objects.filter(user=user, otp=otp).first()
            if not otp_obj:
                messages.error(request, "Invalid OTP.")
                return render(request, "employe/reset_password.html", context)

            if otp_obj.is_expired():
                messages.error(request, "OTP has expired.")
                return render(request, "employe/reset_password.html", context)
            
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, "employe/reset_password.html", context)
            
            try:
                validate_password(new_password, user)
            except ValidationError as e:
                messages.error(request, " ".join(e.messages))
                return render(request, "employe/reset_password.html", context)
            
            user.set_password(new_password)
            user.save()
            
            otp_obj.delete()
            
            messages.success(request, "Password reset successfully. Please login.")
            return redirect('employe:login')
        
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('employe:forget_password')
            
    
    return render(request, "employe/reset_password.html", context)
