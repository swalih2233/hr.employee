from employe.models import Employe, LeaveRequest
from managers.models import Manager, Founder, UnifiedLeaveRequest

def user_context(request):
    context = {
        'profile': None,
        'notification_count': 0,
        'is_manager': False,
        'is_employee': False,
        'is_founder': False,
    }

    if request.user.is_authenticated:
        try:
            founder = Founder.objects.get(user=request.user)
            context['profile'] = founder
            context['is_founder'] = True
            # Founders see all pending requests (both employee and manager)
            emp_pending = LeaveRequest.objects.filter(status='Pending', is_cancelled=False).count()
            mgr_pending = UnifiedLeaveRequest.objects.filter(
                requested_by_role='manager',
                is_approved=False,
                is_rejected=False,
                is_cancelled=False
            ).count()
            context['notification_count'] = emp_pending + mgr_pending
        except Founder.DoesNotExist:
            try:
                manager = Manager.objects.get(user=request.user)
                context['profile'] = manager
                context['is_manager'] = True
                employees = Employe.objects.filter(manager=manager)
                context['notification_count'] = LeaveRequest.objects.filter(employee__in=employees, status='Pending').count()
            except Manager.DoesNotExist:
                try:
                    employee = Employe.objects.get(user=request.user)
                    context['profile'] = employee
                    context['is_employee'] = True
                    subordinates = Employe.objects.filter(reporting_employee=employee)
                    if subordinates.exists():
                        sub_pending = LeaveRequest.objects.filter(
                            employee__in=subordinates, status='Pending', is_cancelled=False
                        ).count()
                        sub_withdrawals = LeaveRequest.objects.filter(
                            employee__in=subordinates,
                            is_withdrawal_requested=True,
                            is_withdrawn=False,
                            withdrawal_rejected=False
                        ).count()
                        context['notification_count'] = sub_pending + sub_withdrawals
                        context['subordinate_leave_count'] = sub_pending + sub_withdrawals
                        context['has_subordinates'] = True
                    else:
                        context['subordinate_leave_count'] = 0
                        context['has_subordinates'] = False
                except Employe.DoesNotExist:
                    pass  # Handle other user types if necessary

    return context
