from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import LeaveRequest
from .forms import LeaveRequestForm
from employe.models import Employe
from managers.models import Manager, Founder

@login_required
def apply_leave(request):
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            
            # 1. Assign employee
            try:
                leave.employee = Employe.objects.get(user=request.user)
            except Employe.DoesNotExist:
                messages.error(request, "User is not an employee.")
                return redirect('some_error_page')  # Or handle appropriately

            # 2. Validate start_date <= end_date
            if leave.start_date > leave.end_date:
                messages.error(request, "Start date cannot be after end date.")
                return render(request, 'leaves/apply_leave.html', {'form': form})

            # Check for overlapping leave requests
            overlapping_leaves = LeaveRequest.objects.filter(
                employee=leave.employee,
                start_date__lte=leave.end_date,
                end_date__gte=leave.start_date,
                status='pending'
            )
            if overlapping_leaves.exists():
                messages.error(request, "You already have a pending leave request that overlaps with these dates.")
                return render(request, 'leaves/apply_leave.html', {'form': form})

            # 3. Calculate total_days
            leave.total_days = (leave.end_date - leave.start_date).days + 1
            leave.save()

            # 4. Send email notification
            try:
                founders = Founder.objects.all()
                founder_emails = [founder.user.email for founder in founders]
                
                email = EmailMessage(
                    'New Leave Request',
                    f'A new leave request has been submitted by {leave.employee}.',
                    'from@example.com',
                    [leave.employee.manager.user.email],
                    cc=founder_emails
                )
                email.send()
            except Exception as e:
                messages.error(request, f"Leave saved, but failed to send email: {e}")
            else:
                messages.success(request, "Leave request submitted successfully.")
                
            return redirect('leaves:leave_history')
    else:
        form = LeaveRequestForm()
    return render(request, 'leaves/apply_leave.html', {'form': form})

@login_required
@require_POST
def update_leave_status(request, pk, status):
    # 1. Allow only managers
    if not hasattr(request.user, 'manager'):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    leave = get_object_or_404(LeaveRequest, pk=pk)
    
    # 2. Update status
    if status in ['approved', 'rejected']:
        leave.status = status
        leave.save()

        # 3. Email employee with CC to founders
        try:
            founders = Founder.objects.all()
            founder_emails = [founder.user.email for founder in founders]
            
            email = EmailMessage(
                f'Leave Request {status.capitalize()}',
                f'Your leave request for {leave.total_days} days has been {status}.',
                'from@example.com',
                [leave.employee.user.email],
                cc=founder_emails
            )
            email.send()
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
        pending_leaves = LeaveRequest.objects.filter(employee__in=employees, status='pending')
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
