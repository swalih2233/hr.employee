from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from employe.models import Employe, LeaveRequest
from .forms import LeaveRequestForm
from managers.models import Manager, Founder

@login_required
def apply_leave(request):
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            
            # Check if the user is a manager or an employee
            is_manager = hasattr(request.user, 'user_manager')
            is_employee = hasattr(request.user, 'user_employee')

            if is_manager:
                leave.manager = request.user.user_manager
                leave.requested_by_role = 'manager'
            elif is_employee:
                leave.employee = request.user.user_employee
                leave.requested_by_role = 'employee'
            else:
                messages.error(request, "Invalid user type.")
                return redirect('some_error_page')

            if leave.start_date > leave.end_date:
                messages.error(request, "Start date cannot be after end date.")
                return render(request, 'leaves/apply_leave.html', {'form': form})

            leave.leave_duration = (leave.end_date - leave.start_date).days + 1
            leave.status = 'Pending'
            leave.save()

            # Send email notification based on the user's role
            from managers.views import send_leave_notification
            if is_manager:
                # A manager is applying for leave, notify all founders
                send_leave_notification(request, leave, 'new_manager_request', None, cc_founder=True)
            elif is_employee:
                # An employee is applying for leave, notify the manager and CC founders
                if leave.employee.manager:
                    manager_email = leave.employee.manager.user.email
                    manager_name = leave.employee.manager.user.get_full_name()
                    send_leave_notification(request, leave, 'new_request', manager_email, manager_name=manager_name, cc_founder=True)
                else:
                    # Fallback to founders if no manager assigned
                    founders = Founder.objects.all()
                    founder_emails = [founder.user.email for founder in founders]
                    if founder_emails:
                        send_leave_notification(request, leave, 'new_request', None, cc_founder=True)
            
            # Send submission confirmation to the user who applied
            send_leave_notification(request, leave, 'submission_confirmation', request.user.email)
            
            messages.success(request, "Leave request submitted successfully.")
            return redirect('leaves:leave_history')
    else:
        form = LeaveRequestForm()
    return render(request, 'leaves/apply_leave.html', {'form': form})

@login_required
@require_POST
def update_leave_status(request, pk, status):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    employee_profile = leave.employee
    
    # 1. Permission check: Only respective manager or founder can take action
    can_action = False
    from common.utils import is_founder, is_manager
    
    if request.user.is_superuser:
        can_action = True
    elif is_founder(request.user):
        can_action = True
    elif is_manager(request.user):
        if employee_profile.manager and employee_profile.manager.user == request.user:
            can_action = True
    
    if not can_action:
        return JsonResponse({'error': 'Permission denied. You do not have permission to action this leave request.'}, status=403)
    
    # 2. Update status
    if status in ['approved', 'rejected']:
        leave.status = status.capitalize()
        if status == 'approved':
            leave.is_approved = True
            leave.approval_date = timezone.now()
        elif status == 'rejected':
            leave.is_rejected = True
            leave.rejection_date = timezone.now()
        leave.save()

        # 3. Email employee
        try:
            from managers.views import send_leave_notification
            send_leave_notification(request, leave, status, leave.employee.user.email, cc_founder=True)
        except Exception as e:
            return JsonResponse({'error': f'Status updated, but email failed: {e}'})

        return JsonResponse({'success': f'Leave request {status}.'})
    
    return JsonResponse({'error': 'Invalid status'}, status=400)

@login_required
def leave_history(request):
    try:
        employee = Employe.objects.get(user=request.user)
        leaves = LeaveRequest.objects.filter(employee=employee)
    except Employe.DoesNotExist:
        leaves = []
        messages.error(request, "User is not an employee.")
    
    return render(request, 'leaves/leave_history.html', {'leaves': leaves})

@login_required
def leave_requests(request):
    if hasattr(request.user, 'manager'):
        manager = request.user.manager
        employees = Employe.objects.filter(manager=manager)
        pending_leaves = LeaveRequest.objects.filter(employee__in=employees, status='Pending')
    else:
        pending_leaves = []
        messages.error(request, "User is not a manager.")
        
    return render(request, 'leaves/leave_requests.html', {'pending_leaves': pending_leaves})

@login_required
def manager_leave_history(request):
    if hasattr(request.user, 'manager'):
        manager = request.user.manager
        employees = Employe.objects.filter(manager=manager)
        leaves = LeaveRequest.objects.filter(employee__in=employees)
    else:
        leaves = []
        messages.error(request, "User is not a manager.")
        
    return render(request, 'leaves/manager_leave_history.html', {'leaves': leaves})
