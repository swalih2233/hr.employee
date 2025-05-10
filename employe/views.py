from django.shortcuts import render,  reverse
from django.shortcuts import HttpResponse

from django.http.response import HttpResponseRedirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required

from common.decorators import allow_employee
from employe.models import *
from managers.models import *
from users.models import *



from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.timezone import now
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
    employe = Employe.objects.get(user=user)
    contact = EmergencyContact.objects.get(employe=employe)
    address = Address.objects.get(employe=employe)
    background = Background.objects.get(employe=employe)
    benefits = Benefits.objects.get(employe=employe)
    identification = Identification.objects.get(employe=employe)
    shedule = WorkSchedule.objects.get(employe=employe)
    holidays = Holiday.objects.all()

    context ={
        'employe': employe,
        'user': user,
        'contact': contact,
        'address': address,
        'background': background,
        'benefits': benefits,
        'identification': identification,
        'schedule': shedule,
        'holidays':holidays
    }

    return render(request, "employe/details.html", context=context)


@login_required(login_url='/login')
@allow_employee
def leaveform(request):
    
    user = request.user
    employe = Employe.objects.get(user=user)

    if request.method =='POST':
        subject = request.POST.get('subject')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        leave_type = request.POST.get('leave_type')
        description = request.POST.get('description')
        file = request.FILES.get('file')

        leaveform = LeaveReaquest.objects.create(
            subject=subject,
            leave_type=leave_type,
            description= description,
            file = file,
            employe=employe,
            start_date = start_date,
            end_date = end_date
        )
        leaveform.save()
        return HttpResponseRedirect(reverse("employe:details"))
    return render(request, "employe/leaveform.html")


def logout(request):
    auth_logout(request)
    return HttpResponseRedirect(reverse("employe:login"))


def login(request):
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password")

        if email and password:
            user = authenticate(request, email=email, password=password)
            if user is not None:
                auth_login(request, user)
                return HttpResponseRedirect(reverse("employe:details"))
            else:
                messages.error(request, "Invalid credentials, please check your email and password.")
                return render(request, "employe/login.html", {"title": "Login"})
        
        messages.error(request, "Email and password are required.")
        return render(request, "employe/login.html", {"title": "Login"})
    
    return render(request, "employe/login.html", {"title": "Login"})


@login_required(login_url='/login')
@allow_employee
def leavelist(request):
    instances = LeaveReaquest.objects.all()

    # Calculate leave duration for each instance
    for instance in instances:
        instance.leave_duration = (instance.end_date - instance.start_date).days + 1
    
    return render(request, "employe/leavelist.html", {'instances': instances})




@login_required(login_url='/login')
@allow_employee
def viewlist(request, id):
    
    leave_request = LeaveReaquest.objects.get(id=id)
    employee = leave_request.employe
    user = employee.user 
    
    return render(request, 'employe/viewlist.html', {
        'user': user,
        'employe': employee,
        'leave_request': leave_request,
    })



@login_required(login_url='/login')
@allow_employee
def edit_employe(request, id):
    employe = Employe.objects.get(id=id)
    user = employe.user
    contact = EmergencyContact.objects.get(employe=employe)
    address = Address.objects.get(employe=employe)
    background = Background.objects.get(employe=employe)
    benefits = Benefits.objects.get(employe=employe)
    identification = Identification.objects.get(employe=employe)
    schedule = WorkSchedule.objects.get(employe=employe)

    user_date_of_birth = employe.user.date_of_birth.strftime('%Y-%m-%d') if employe.user.date_of_birth else ''

    date_joining = employe.date_of_joining.strftime('%Y-%m-%d') if employe.date_of_joining else ''

    # Format the time fields
    schedule_start_time = schedule.start_time.strftime('%H:%M') if schedule.start_time else ''
    schedule_end_time = schedule.end_time.strftime('%H:%M') if schedule.end_time else ''

    if request.method == 'POST':
        # User details
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.employe_id = request.POST.get('employe_id')
        user.phone_number = request.POST.get('phone_number')
        user.date_of_birth = request.POST.get('date_of_birth')
        user.gender = request.POST.get('gender')
        user.maritul_status = request.POST.get('maritul_status')
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
        employe.date_of_joining = request.POST.get('date_of_joining')
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
        benefits.account_number = request.POST.get('account_number')
        benefits.branch_name = request.POST.get('branch_name')
        benefits.ifsc_code = request.POST.get('ifsc_code')
        benefits.pancard = request.POST.get('pancard')
        benefits.pf_fund = request.POST.get('pf_fund')
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
        schedule.start_time = request.POST.get('start_time')
        schedule.end_time = request.POST.get('end_time')
        schedule.save()

        return HttpResponseRedirect(reverse("employe:detail"))

    context = {
        'employe': employe,
        'user': user,
        'contact': contact,
        'address': address,
        'background': background,
        'benefits': benefits,
        'identification': identification,
        'schedule': schedule,
        'user_date_of_birth': user_date_of_birth,
        'schedule_start_time': schedule_start_time,
        'schedule_end_time': schedule_end_time,
        'date_joining': date_joining
    }

    return render(request, "employe/edit_employe.html", context=context)

User = get_user_model()

# def forget_password(request):
#     context = {"title": "Forget Password"}
    
#     if request.method == "POST":
#         email = request.POST.get("email")
        
#         try:
#             validate_email(email)
#             user = User.objects.get(email=email)  # Handle custom user models
            
#             otp = secrets.randbelow(899999) + 100000
#             OTP.objects.create(user=user, otp=otp)
            
#             send_mail(
#                 subject='Password Reset OTP',
#                 message=f'Your OTP for resetting the password is {otp}',
#                 from_email=settings.EMAIL_HOST_USER,
#                 recipient_list=[email],
#                 fail_silently=False,
#             )
            
#             request.session['reset_user_email'] = email
#             messages.success(request, "If this email is registered, an OTP has been sent.")
#             return HttpResponseRedirect(reverse('employe:reset_password'))
        
#         except ValidationError:
#             messages.error(request, "Invalid email format.")
#         except User.DoesNotExist:
#             messages.success(request, "If this email is registered, an OTP has been sent.")
#         except Exception as e:
#             messages.error(request, f"An error occurred: {e}")
    
#     return render(request, "employe/forget_password.html", context)





# def reset_password(request):
#     context = {"title": "Reset Password"}
    
#     if request.method == "POST":
#         otp = request.POST.get("otp")
#         new_password = request.POST.get("new_password")
#         confirm_password = request.POST.get("confirm_password")
        
#         email = request.session.get('reset_user_email')
#         try:
#             user = User.objects.get(email=email)
#             otp_obj = OTP.objects.filter(user=user, otp=otp).first()
            
#             if not otp_obj or otp_obj.is_expired():
#                 messages.error(request, "Invalid or expired OTP.")
#             elif new_password != confirm_password:
#                 messages.error(request, "Passwords do not match.")
#             else:
#                 try:
#                     validate_password(new_password, user)
#                 except ValidationError as e:
#                     messages.error(request, " ".join(e.messages))
#                     return render(request, "employe/reset_password.html", context)

#                 # Save the new password
#                 user.password = make_password(new_password)
#                 user.save()
                
#                 # Remove the OTP after successful reset
#                 otp_obj.delete()
#                 messages.success(request, "Password reset successfully. Please login.")
                
#                 # Redirect to login page
#                 return HttpResponseRedirect(reverse('employe:login'))
        
#         except User.DoesNotExist:
#             messages.error(request, "User does not exist.")
    
#     return render(request, "employe/reset_password.html", context)


# def forget_password(request):
    
#     if request.method == "POST":
#         email = request.POST.get("email")

#         if User.objects.filter(email=email).exists():

#             user = User.objects.get(email=email)
            
#             otp = secrets.randbelow(899999) + 100000
#             OTP.objects.create(user=user, otp=otp)
            
#             context = ssl._create_unverified_context()
#             with smtplib.SMTP('smtp.gmail.com', 587) as server:
#                 server.starttls(context=context)
#                 server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
#                 send_mail(
#                     'Reset Password OTP',
#                     f'Your OTP for resetting the password is {otp}',
#                     settings.EMAIL_HOST_USER,
#                     [email],
#                     fail_silently=False,
#                 )
        
#             return HttpResponseRedirect(reverse('employe:reset_password'))
#         else:
#             context = {
#                 "title": "Forget Password",
#                 "message": "Invalid email address"
#             }
#         return render(request, "employe/forget_password.html", context)
    
#     context = {
#         "title": "Forget Password",
#     }

            
#     return render(request, "employe/forget_password.html", context)

def forget_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            
            # Generate OTP
            otp = secrets.randbelow(899999) + 100000
            expires_at = timezone.now() + timedelta(minutes=10)  # Set OTP expiration time (10 minutes)
            
            # Create OTP with expiration time
            OTP.objects.create(user=user, otp=otp, expires_at=expires_at)
            
            # Save email in session
            request.session['reset_user_email'] = email
            
            # Send OTP via email
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


def reset_password(request):
    context = {"title": "Reset Password"}
    
    if request.method == "POST":
        otp = request.POST.get("otp")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        
        # Retrieve email from session
        email = request.session.get('reset_user_email')
        if not email:
            messages.error(request, "Session expired. Please restart the password reset process.")
            return redirect('employe:forget_password')
        
        try:
            # Get the user based on the email
            user = User.objects.get(email=email)
            
            # Retrieve and validate the OTP
            otp_obj = OTP.objects.filter(user=user, otp=otp).first()
            if not otp_obj:
                messages.error(request, "Invalid OTP.")
                return render(request, "employe/reset_password.html", context)

            if otp_obj.is_expired():
                messages.error(request, "OTP has expired.")
                return render(request, "employe/reset_password.html", context)
            
            # Check if passwords match
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, "employe/reset_password.html", context)
            
            # Validate new password
            try:
                validate_password(new_password, user)
            except ValidationError as e:
                messages.error(request, " ".join(e.messages))
                return render(request, "employe/reset_password.html", context)
            
            # Set and save the new password
            user.set_password(new_password)
            user.save()
            
            # Delete the OTP after successful password reset
            otp_obj.delete()
            
            messages.success(request, "Password reset successfully. Please login.")
            return redirect('employe:login')
        
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('employe:forget_password')
            
    
    return render(request, "employe/reset_password.html", context)