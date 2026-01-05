from leaves.models import LeaveRequest
from employe.models import Employe
from managers.models import Manager, Founder

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
            # Founders see all pending requests
            context['notification_count'] = LeaveRequest.objects.filter(status='pending').count()
        except Founder.DoesNotExist:
            try:
                manager = Manager.objects.get(user=request.user)
                context['profile'] = manager
                context['is_manager'] = True
                employees = Employe.objects.filter(manager=manager)
                context['notification_count'] = LeaveRequest.objects.filter(employee__in=employees, status='pending').count()
            except Manager.DoesNotExist:
                try:
                    employee = Employe.objects.get(user=request.user)
                    context['profile'] = employee
                    context['is_employee'] = True
                except Employe.DoesNotExist:
                    pass  # Handle other user types if necessary

    return context
