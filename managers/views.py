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
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from users.models import User
from users.models import OTP  # Assuming OTP is in the common app
import random
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.validators import validate_email
import secrets

@login_required(login_url='/managers/login')
@allow_manager
def index(request):
    m_count = Manager.objects.all().count()
    managers = Manager.objects.all()
    employes = Employe.objects.all()
    e_count = Employe.objects.all().count()

    leave_count = LeaveReaquest.objects.filter(is_approved=False).count()
    
    context ={
        "title":"employe management",
        "employes": employes,
        "managers": managers,
        "m_count": m_count,
        "e_count": e_count,
        "leave_count":leave_count
    }
    
    return render(request, "managers/index.html", context=context)


def login(request):
    context = {"title": "Login"}
    
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password")

        if email and password:
            user = authenticate(request, email=email, password=password)
            
            if user:
                if user.is_superuser:
                    auth_login(request, user)
                    user.is_manager = True
                    user.save()
                    manager, created = Manager.objects.get_or_create(user=user)

                    # Create or get related manager models
                    related_models = [
                        EmergencyContactManager,
                        AddressManager,
                        BackgroundManager,
                        BenefitsManager,
                        IdentificationManager,
                        WorkScheduleManager 
                    ]

                    for model in related_models:
                        model.objects.get_or_create(manager=manager)

                    return HttpResponseRedirect(reverse("managers:index"))
                else:
                    # If user is not a superuser, handle this error
                    messages.error(request, "Access restricted")
            else:
                # If authentication failed (wrong password or email)
                messages.error(request, "Invalid email or password")
        else:
            messages.error(request, "Email and password are required")

    return render(request, "managers/login.html", context)


def logout(request):
    auth_logout(request)
    return HttpResponseRedirect(reverse("managers:login"))


@login_required(login_url='/managers/login')
@allow_manager
def account(request):
    user = request.user
    manager = Manager.objects.get(user=user)
    context = {
        "title": f"{manager.user.first_name} {manager.user.last_name}", 
        "manager": manager
    }
    return render(request, "managers/details.html", context=context)


@login_required(login_url='/managers/login')
@allow_manager
def manager_details(request, id):
    manager = Manager.objects.get(id=id)
    context = {
        "title": f"{manager.user.first_name} {manager.user.last_name}", 
        "manager": manager
    }
    return render(request, "managers/details.html", context=context)



@login_required(login_url='/managers/login')
@allow_manager
def manager_add(request):
    # Initialize the context to pass to the template
    context = {
        'first_name': '',
        'last_name': '',
        'phone': '',
        'joining_date': '',
        'job_role': ''
    }

    if request.method == 'POST':
        # Extract form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        image = request.FILES.get('image')
        joining_date = request.POST.get('joining_date')
        job_role = request.POST.get('job_role')

        # Update context with form data to repopulate the form in case of errors
        context.update({
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'joining_date': joining_date,
            'job_role': job_role
        })

        # Check if the user with the provided email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "A user with this email already exists.")
            return render(request, "managers/manager_add.html", context)

        try:
            # Print the extracted data to debug
            print("Form Data:", first_name, last_name, email, phone, password, image, joining_date, job_role)

            # Create the new user
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone,  # Ensure your User model has phone_number field
                password=password,
                is_manager=True,
                is_superuser=True
            )
            user.save()

            # Create the employee profile
            manager = Manager.objects.create(
                user=user,
                image=image,
                date_of_joining=joining_date,
                department=job_role
            )
            manager.save()

            # Create or get related manager models
            related_models = [
                EmergencyContactManager,
                AddressManager,
                BackgroundManager,
                BenefitsManager,
                IdentificationManager,
                WorkScheduleManager 
            ]

            for model in related_models:
                model.objects.get_or_create(manager=manager)

            messages.success(request, "Manager added successfully.")
            return redirect(reverse("managers:index"))

        except Exception as e:
            # Print the error stack trace for debugging
            error_trace = traceback.format_exc()
            print(f"Error occurred: {error_trace}")
            # Display the error message to the user
            messages.error(request, f"An error occurred: {error_trace}")
            return render(request, "managers/manager_add.html", context)

    # GET request: simply render the form with the empty context
    return render(request, "managers/manager_add.html", context)



@login_required(login_url='/managers/login')
@allow_manager
def manager_edit(request, id):
    employe = Manager.objects.get(id=id)
    user = employe.user
    contact = EmergencyContactManager.objects.get(manager=employe)
    address = AddressManager.objects.get(manager=employe)
    background = BackgroundManager.objects.get(manager=employe)
    benefits = BenefitsManager.objects.get(manager=employe)
    identification = IdentificationManager.objects.get(manager=employe)
    schedule = WorkScheduleManager.objects.get(manager=employe)

    user_date_of_birth = employe.user.date_of_birth.strftime('%Y-%m-%d') if employe.user.date_of_birth else ''

    date_joining = employe.date_of_joining.strftime('%Y-%m-%d') if employe.date_of_joining else ''

    # Format the time fields
    schedule_start_time = schedule.start_time.strftime('%H:%M') if schedule.start_time else ''
    schedule_end_time = schedule.end_time.strftime('%H:%M') if schedule.end_time else ''
    
   

    if request.method == 'POST':
        # User details
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.phone_number = request.POST.get('phone_number')
        user.date_of_birth = request.POST.get('date_of_birth')
        user.gender = request.POST.get('gender')
        user.maritul_status = request.POST.get('maritul_status')
        user.save()

        # Emergency Contact
        contact.country = request.POST.get('emergency_country')
        contact.city = request.POST.get('emergency_city')
        contact.pincode = request.POST.get('emergency_pincode')
        contact.save()

        # Employee details
        employe.user.employe_id = request.POST.get('employe_id')
        employe.department = request.POST.get('department')
        employe.designation = request.POST.get('designation')
        employe.date_of_joining = request.POST.get('date_of_joining')
        employe.employment_Type = request.POST.get('employment_Type')
        employe.reporting_manager = request.POST.get('reporting_manager')
        employe.work_location = request.POST.get('work_location')
        employe.save()

        # Address
        address.Permanent_address = request.POST.get('Permanent_address')
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

        return redirect(reverse("managers:index"))

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

    return render(request, "managers/edit_employe.html", context=context)



@login_required(login_url='/managers/login')
@allow_manager
def leavelist(request):
    instances = LeaveReaquest.objects.all()

    # Calculate leave duration for each instance
    for instance in instances:
        instance.leave_duration = (instance.end_date - instance.start_date).days + 1
    
    return render(request, "managers/leavelist.html", {'instances': instances})



@login_required(login_url='/managers/login')
@allow_manager
def viewlist(request, id):
    
    leave_request = LeaveReaquest.objects.get(id=id)
    employee = leave_request.employe
    user = employee.user 
    
    return render(request, 'managers/viewlist.html', {
        'user': user,
        'employe': employee,
        'leavereaquest': leave_request,
    })

# @login_required(login_url='/managers/login')
# @allow_manager
# def approve_leave(request, id):
#     leave_request = LeaveReaquest.objects.get(id=id)  # Fixed typo in LeaveRequest
#     employee = leave_request.employe  # Fixed typo in employee

#     # Calculate the number of days between start_date and end_date
#     leave_duration = (leave_request.end_date - leave_request.start_date).days + 1

#     # Approve the leave request
#     leave_request.is_approved = True
#     leave_request.save()

#     # Check the type of leave: regular, medical, or PR leave
#     if leave_request.leave_type == 'ML':  # Assuming 'ML' means Medical Leave
#         # Deduct from available medical leave balance and increase medical leaves taken
#         employee.medical_leaves_taken += leave_duration
#         employee.available_medical_leaves -= leave_duration

#     elif leave_request.leave_type == 'PR':  # Assuming 'PR' means some carryforward leave type
#         # Deduct from carryforward leave balance and increase carryforward leaves taken
#         employee.carryforward_leaves_taken += leave_duration
#         employee.carryforward_available_leaves -= leave_duration

#     else:
#         # Deduct from available regular leave balance and increase regular leaves taken
#         employee.leaves_taken += leave_duration
#         employee.available_leaves -= leave_duration

#     # Save the updated employee leave balance
#     employee.save()

#     # Notify the user and redirect to the manager's index page
#     messages.success(request, f"Leave request approved successfully for {leave_duration} days.")
#     return redirect(reverse("managers:index"))


# @login_required(login_url='/managers/login')
# @allow_manager
# def approve_leave(request, id):
#     leave_request = LeaveReaquest.objects.get(id=id)  # Fixed typo in LeaveReaquest
#     employee = leave_request.employe  # Fixed typo in employee

#     # Calculate the number of days between start_date and end_date
#     leave_duration = (leave_request.end_date - leave_request.start_date).days + 1

#     # Approve the leave request
#     leave_request.is_approved = True
#     leave_request.approval_date = timezone.now()  # Set the approval date
#     leave_request.save()

#     # Check the type of leave: regular, medical, or PR leave
#     if leave_request.leave_type == 'ML':  # Assuming 'ML' means Medical Leave
#         # Deduct from available medical leave balance and increase medical leaves taken
#         employee.medical_leaves_taken += leave_duration
#         employee.available_medical_leaves -= leave_duration

#     elif leave_request.leave_type == 'PR':  # Assuming 'PR' means some carryforward leave type
#         # Deduct from carryforward leave balance and increase carryforward leaves taken
#         employee.carryforward_leaves_taken += leave_duration
#         employee.carryforward_available_leaves -= leave_duration

#     else:
#         # Deduct from available regular leave balance and increase regular leaves taken
#         employee.leaves_taken += leave_duration
#         employee.available_leaves -= leave_duration

#     # Save the updated employee leave balance
#     employee.save()

#     # Notify the user and redirect to the manager's index page
#     messages.success(request, f"Leave request approved successfully for {leave_duration} days.")
#     return redirect(reverse("managers:index"))



@login_required(login_url='/managers/login')
@allow_manager
def approve_leave(request, id):
    leave_request = LeaveReaquest.objects.get(id=id)
    employee = leave_request.employe

    # Calculate the number of leave days excluding holidays, Saturdays, and Sundays
    leave_duration = (leave_request.end_date - leave_request.start_date).days + 1
    leave_days = []

    current_day = leave_request.start_date
    while current_day <= leave_request.end_date:
        # Check if it's a weekend or a holiday
        if current_day.weekday() >= 5:  # 5 and 6 correspond to Saturday and Sunday
            pass
        elif Holiday.objects.filter(date=current_day).exists():  # Check if it's a holiday
            pass
        else:
            leave_days.append(current_day)
        
        current_day += timedelta(days=1)

    # The actual number of leave days excluding weekends and holidays
    actual_leave_days = len(leave_days)

    # Approve the leave request and save the calculated leave duration
    leave_request.is_approved = True
    leave_request.approval_date = timezone.now()  # Set the approval date
    leave_request.leave_duration = actual_leave_days  # Save the calculated leave days
    leave_request.save()

    # Check the type of leave and adjust balances
    if leave_request.leave_type == 'ML':  # Medical Leave
        employee.medical_leaves_taken += actual_leave_days
        employee.available_medical_leaves -= actual_leave_days
    elif leave_request.leave_type == 'PR':  # Privilege Leave
        employee.carryforward_leaves_taken += actual_leave_days
        employee.carryforward_available_leaves -= actual_leave_days
    else:  # Casual Leave
        employee.leaves_taken += actual_leave_days
        employee.available_leaves -= actual_leave_days

    # Save the updated employee leave balance
    employee.save()

    # Notify the user and redirect to the manager's index page
    messages.success(request, f"Leave request approved successfully for {actual_leave_days} days.")
    return redirect(reverse("managers:index"))



@login_required(login_url='/managers/login')
@allow_manager
def update_yearly(request):
    employees = Employe.objects.all()
    for employee in employees:
       if employee.available_leaves >= 10:
            employee.available_leaves = 18
            employee.leaves_taken  = 0
            employee.available_medical_leaves= 14
            employee.carryforward_available_leaves=6
       
            employee.save()

    return redirect(reverse("managers:index"))



@login_required(login_url='/managers/login')
@allow_manager
def update_march(request):
    employees = Employe.objects.all()
    for employee in employees:
        # Reset carryforward_available_leaves to 0 for all employees, regardless of leave count
        employee.carryforward_available_leaves = 0
        employee.carryforward_leaves_taken = 0
        
        # Optionally, cap available leaves at 18 if it exceeds
        if employee.available_leaves > 18:
            employee.available_leaves = 18

        employee.save()

    return redirect(reverse("managers:index"))



@login_required(login_url='/managers/login')
@allow_manager
def add_employe(request):
     # Initialize the context to pass to the template
    context = {
        'first_name': '',
        'last_name': '',
        'phone': '',
        'joining_date': '',
        'job_role': ''
    }

    if request.method == 'POST':
        # Extract form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        employe_id= request.POST.get('employe_id')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        image = request.FILES.get('image')
        joining_date = request.POST.get('joining_date')
        job_role = request.POST.get('job_role')

        # Update context with form data to repopulate the form in case of errors
        context.update({
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'joining_date': joining_date,
            'job_role': job_role,
            'employe_id':employe_id
        })

        # Check if the user with the provided email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "A user with this email already exists.")
            return render(request, "managers/add_employe.html", context)

        try:
            # Print the extracted data to debug
            print("Form Data:", first_name, last_name, email, phone, password, image, joining_date, job_role)

            # Create the new user
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone,  # Ensure your User model has phone_number field
                password=password,
                is_employee = True,
                employe_id= employe_id
            )
            user.save()

            # Create the employee profile
            employe = Employe.objects.create(
                user=user,
                image=image,
                date_of_joining=joining_date,
                department=job_role
            )
            employe.save()

            # Create or get related manager models
            related_models = [
                EmergencyContact,
                Address,
                Background,
                Benefits,
                Identification,
                WorkSchedule
            ]

            for model in related_models:
                model.objects.get_or_create(employe=employe)

            messages.success(request, "Employee added successfully.")
            return redirect(reverse("managers:index"))

        except Exception as e:
            # Print the error stack trace for debugging
            error_trace = traceback.format_exc()
            print(f"Error occurred: {error_trace}")
            # Display the error message to the user
            messages.error(request, f"An error occurred: {error_trace}")
            return render(request, "managers/add_employe.html", context)

    # GET request: simply render the form with the empty context
    return render(request, "managers/add_employe.html", context)


@login_required(login_url='/managers/login')
@allow_manager
def edit_employe(request, id):
    # Fetch the employe or return 404 if it doesn't exist
    employe = get_object_or_404(Employe, id=id)
    user = employe.user

    # Use get_or_create for related objects to ensure they exist
    contact, _ = EmergencyContact.objects.get_or_create(employe=employe)
    address, _ = Address.objects.get_or_create(employe=employe)
    background, _ = Background.objects.get_or_create(employe=employe)
    benefits, _ = Benefits.objects.get_or_create(employe=employe)
    identification, _ = Identification.objects.get_or_create(employe=employe)
    schedule, _ = WorkSchedule.objects.get_or_create(employe=employe)

    # Format date and time fields safely
    user_date_of_birth = employe.user.date_of_birth.strftime('%Y-%m-%d') if employe.user.date_of_birth else ''
    date_joining = employe.date_of_joining.strftime('%Y-%m-%d') if employe.date_of_joining else ''
    schedule_start_time = schedule.start_time.strftime('%H:%M') if schedule.start_time else ''
    schedule_end_time = schedule.end_time.strftime('%H:%M') if schedule.end_time else ''

    if request.method == 'POST':
        # Update user details
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.phone_number = request.POST.get('phone_number')
        user.date_of_birth = request.POST.get('date_of_birth')
        user.gender = request.POST.get('gender')
        user.maritul_status = request.POST.get('maritul_status')
        user.save()

        # Update Emergency Contact
        contact.contact_name = request.POST.get('contact_name')
        contact.contact_number = request.POST.get('contact_number')
        contact.relationship = request.POST.get('relationship')
        contact.country = request.POST.get('emergency_country')
        contact.city = request.POST.get('emergency_city')
        contact.pincode = request.POST.get('emergency_pincode')
        contact.save()

        # Update Employee details
        employe.user.employe_id = request.POST.get('employe_id')
        employe.department = request.POST.get('department')
        employe.designation = request.POST.get('designation')
        employe.date_of_joining = request.POST.get('date_of_joining')
        employe.employment_Type = request.POST.get('employment_Type')
        employe.reporting_manager = request.POST.get('reporting_manager')
        employe.work_location = request.POST.get('work_location')
        employe.employe_status = request.POST.get('employe_status')
        employe.save()

        # Update Address
        address.permanent_address = request.POST.get('permanent_address')
        address.country = request.POST.get('country')
        address.city = request.POST.get('city')
        address.pincode = request.POST.get('pincode')
        address.save()

        # Update Benefits
        benefits.salary_details = request.POST.get('salary_details')
        benefits.bank_name = request.POST.get('bank_name')
        benefits.account_number = request.POST.get('account_number')
        benefits.branch_name = request.POST.get('branch_name')
        benefits.ifsc_code = request.POST.get('ifsc_code')
        benefits.pancard = request.POST.get('pancard')
        benefits.pf_fund = request.POST.get('pf_fund')
        benefits.state_insurance_number = request.POST.get('state_insurance_number')
        benefits.save()

        # Update Background
        background.educational_qualifications = request.POST.get('educational_qualifications')
        background.previous_details = request.POST.get('previous_details')
        background.save()

        # Update Identification
        identification.work_authorization = request.POST.get('work_authorization')
        identification.save()

        # Update Work Schedule
        schedule.start_time = request.POST.get('start_time')
        schedule.end_time = request.POST.get('end_time')
        schedule.save()

        return redirect(reverse("managers:index"))

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
        'date_joining': date_joining,
    }

    return render(request, "managers/edit_employe.html", context=context)


@login_required(login_url='/managers/login')
@allow_manager
def details(request, id):
    employe = Employe.objects.get(id=id)
    user = employe.user
    contact = EmergencyContact.objects.get(employe=employe)
    address = Address.objects.get(employe=employe)
    background = Background.objects.get(employe=employe)
    benefits = Benefits.objects.get(employe=employe)
    identification = Identification.objects.get(employe=employe)
    shedule = WorkSchedule.objects.get(employe=employe)

    context ={
        'employe': employe,
        'user': user,
        'contact': contact,
        'address': address,
        'background': background,
        'benefits': benefits,
        'identification': identification,
        'schedule': shedule,
    }
    return render(request, "managers/details.html", context=context)


@login_required(login_url='/managers/login')
@allow_manager
def manager_details(request, id):
    employe = Manager.objects.get(id=id)
    user = employe.user
    contact = EmergencyContactManager.objects.get(manager=employe)
    address = AddressManager.objects.get(manager=employe)
    background = BackgroundManager.objects.get(manager=employe)
    benefits = BenefitsManager.objects.get(manager=employe)
    identification = IdentificationManager.objects.get(manager=employe)
    shedule = WorkScheduleManager.objects.get(manager=employe)

    context ={
        'employe': employe,
        'user': user,
        'contact': contact,
        'address': address,
        'background': background,
        'benefits': benefits,
        'identification': identification,
        'schedule': shedule,
    }
    return render(request, "managers/details.html", context=context)


@login_required(login_url='/managers/login')
@allow_manager
def reject_leave(request, id):
    leave_request = LeaveReaquest.objects.get(id=id)
    leave_request.is_rejected = True
    leave_request.rejection_date = timezone.now()  # Set rejection time
    leave_request.save()

    # Notify the user and redirect to the manager's index page
    messages.error(request, "Leave request has been rejected.")
    return redirect(reverse("managers:index"))


@login_required(login_url='/managers/login')
@allow_manager
def add_holiday(request):
    # Fetch all holidays to display in the list
    holidays = Holiday.objects.all()

    if request.method == 'POST':
        # Retrieve form data
        title = request.POST.get('title')
        date = request.POST.get('date')

        # Create a new Holiday object and save it
        holiday = Holiday(title=title, date=date)
        holiday.save()

        # Success message
        messages.success(request, "Holiday added successfully!")
        return redirect('managers:add_holiday')

    # Render the add holiday form and list of holidays
    return render(request, 'managers/add_holiday.html', {
        'holidays': holidays
    })
  


@login_required(login_url='/managers/login')
@allow_manager
def delete_holiday(request, id):
    holiday = get_object_or_404(Holiday, id=id)
    
    if request.method == 'POST':
        holiday.delete()
        messages.success(request, "Holiday deleted successfully!")
    
    return redirect('managers:add_holiday')  # Redirect to the list of holidays after deletion


@login_required(login_url='/managers/login')
@allow_manager
def bulk_delete_holidays(request):
    if request.method == 'POST':
        # Delete all holiday entries
        Holiday.objects.all().delete()
        messages.success(request, "All holidays deleted successfully!")
        
    return redirect('managers:add_holiday')  # Redirect to the list after bulk deletio


# User = get_user_model()

# def manager_forget_password(request):
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
#             return HttpResponseRedirect(reverse('managers:reset_password'))
        
#         except ValidationError:
#             messages.error(request, "Invalid email format.")
#         except User.DoesNotExist:
#             messages.success(request, "If this email is registered, an OTP has been sent.")
#         except Exception as e:
#             messages.error(request, f"An error occurred: {e}")
    
#     return render(request, "managers/forget_password.html", context)


# def manager_reset_password(request):
#     context = {"title": "Reset Password"}
    
#     if request.method == "POST":
#         otp = request.POST.get("otp")
#         new_password = request.POST.get("new_password")
#         confirm_password = request.POST.get("confirm_password")
        
#         email = request.session.get('manager_reset_email')
#         try:
#             user = User.objects.get(email=email, is_manager=True)  # Ensure the user is a manager
#             otp_obj = OTP.objects.filter(user=user, otp=otp).first()
            
#             if not otp_obj:
#                 messages.error(request, "Invalid or expired OTP.")
#             elif new_password != confirm_password:
#                 messages.error(request, "Passwords do not match.")
#             else:
#                 try:
#                     validate_password(new_password, user)
#                 except ValidationError as e:
#                     messages.error(request, " ".join(e.messages))
#                     return render(request, "managers/reset_password.html", context)

#                 # Save the new password
#                 user.password = make_password(new_password)
#                 user.save()
#                 otp_obj.delete()  # Remove OTP after successful reset
#                 messages.success(request, "Password reset successfully. Please login.")
#                 return redirect('managers:login')  # Redirect to login page
#         except User.DoesNotExist:
#             messages.error(request, "User does not exist.")
    
#     return render(request, "managers/reset_password.html", context)


def manager_forget_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        # Validate email format
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            context = {
                "title": "Forget Password",
                "message": "Invalid email format"
            }
            return render(request, "managers/forget_password.html", context)

        # Check if the email exists in the database
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            context = {
                "title": "Forget Password",
                "message": "Email not found in our records. Please try again."
            }
            return render(request, "managers/forget_password.html", context)

        # Generate OTP (6 digits)
        otp = secrets.randbelow(899999) + 100000

        # Set OTP expiration time (e.g., 10 minutes from now)
        otp_expiry_time = timezone.now() + timedelta(minutes=10)

        # Create OTP entry in the database with an expiration time
        OTP.objects.create(user=user, otp=otp, expires_at=otp_expiry_time)

        # Send OTP via email (same as before)
        try:
            context = ssl._create_unverified_context()
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls(context=context)
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                send_mail(
                    'Reset Password OTP',
                    f'Your OTP for resetting the password is {otp}. It will expire in 10 minutes.',
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )
            
            # Store the email in session for later use
            request.session['reset_user_email'] = email

            # Redirect to reset password page
            return HttpResponseRedirect(reverse('managers:reset_password'))

        except smtplib.SMTPException as e:
            messages.error(request, "Error sending OTP email. Please try again later.")
            return render(request, "managers/forget_password.html", {"title": "Forget Password"})

    # If the request method is GET, show the form
    context = {
        "title": "Forget Password",
    }
    return render(request, "managers/forget_password.html", context)



def manager_reset_password(request):
    context = {"title": "Reset Password"}

    # Retrieve the email from session
    email = request.session.get('reset_user_email')

    if not email:
        messages.error(request, "Session expired. Please restart the password reset process.")
        return redirect('managers:forget_password')

    if request.method == "POST":
        otp = request.POST.get("otp")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        try:
            # Retrieve user by email
            user = get_user_model().objects.get(email=email)
            otp_obj = OTP.objects.filter(user=user, otp=otp).first()

            # Validate OTP
            if not otp_obj or otp_obj.is_expired():
                messages.error(request, "Invalid or expired OTP.")
            elif new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
            else:
                try:
                    # Validate password strength (optional)
                    validate_password(new_password, user)
                except ValidationError as e:
                    messages.error(request, " ".join(e.messages))
                    return render(request, "managers/reset_password.html", context)

                # Save the new password
                user.set_password(new_password)
                user.save()

                # Remove OTP after successful reset
                otp_obj.delete()
                messages.success(request, "Password reset successfully. Please login.")

                # Redirect to login page
                return HttpResponseRedirect(reverse('managers:login'))

        except get_user_model().DoesNotExist:
            messages.error(request, "User does not exist.")

    return render(request, "managers/reset_password.html", context)