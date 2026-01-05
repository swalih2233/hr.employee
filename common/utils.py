"""
Utility functions for role management and access control
"""
from django.utils import timezone

def get_user_role(user):
    """
    Get the primary role of a user
    Returns: 'founder', 'manager', 'employee', or None
    """
    if not user.is_authenticated:
        return None
    
    # Check if user is a founder (highest priority)
    try:
        from managers.models import Founder
        Founder.objects.get(user=user)
        return 'founder'
    except Founder.DoesNotExist:
        pass
    
    # Check if user is a manager
    if user.is_manager:
        return 'manager'
    
    # Check if user is an employee
    if user.is_employee:
        return 'employee'
    
    return None


def get_user_roles(user):
    """
    Get all roles of a user
    Returns: list of roles ['founder', 'manager', 'employee']
    """
    if not user.is_authenticated:
        return []
    
    roles = []
    
    # Check if user is a founder
    try:
        from managers.models import Founder
        Founder.objects.get(user=user)
        roles.append('founder')
    except Founder.DoesNotExist:
        pass
    
    # Check if user is a manager
    if user.is_manager:
        roles.append('manager')
    
    # Check if user is an employee
    if user.is_employee:
        roles.append('employee')
    
    return roles


def is_founder(user):
    """Check if user is a founder"""
    try:
        from managers.models import Founder
        Founder.objects.get(user=user)
        return True
    except Founder.DoesNotExist:
        return False


def is_manager(user):
    """Check if user is a manager (but not necessarily a founder)"""
    return user.is_manager and user.is_authenticated


def is_employee(user):
    """Check if user is an employee"""
    return user.is_employee and user.is_authenticated


def can_approve_employee_leave(user):
    """Check if user can approve employee leave requests"""
    return is_founder(user) or is_manager(user)


def can_approve_manager_leave(user):
    """Check if user can approve manager leave requests"""
    return is_founder(user)


def get_user_profile(user):
    """
    Get the user's profile object based on their role
    Returns: Founder, Manager, or Employee object
    """
    if not user.is_authenticated:
        return None
    
    # Try to get founder profile first
    try:
        from managers.models import Founder
        return Founder.objects.get(user=user)
    except Founder.DoesNotExist:
        pass
    
    # Try to get manager profile
    if user.is_manager:
        try:
            from managers.models import Manager
            return Manager.objects.get(user=user)
        except Manager.DoesNotExist:
            pass
    
    # Try to get employee profile
    if user.is_employee:
        try:
            from employe.models import Employe
            return Employe.objects.get(user=user)
        except Employe.DoesNotExist:
            pass
    
    return None


def get_dashboard_url(user):
    """
    Get the appropriate dashboard URL for the user based on their role
    """
    primary_role = get_user_role(user)
    
    if primary_role == 'founder':
        return '/managers/'  # Founders use manager dashboard
    elif primary_role == 'manager':
        return '/managers/'
    elif primary_role == 'employee':
        return '/'  # Employee dashboard
    else:
        return '/managers/login/'


def generate_manager_id():
    """Generate a unique manager ID"""
    import random
    import string
    from managers.models import Manager
    
    while True:
        # Generate ID like MGR001, MGR002, etc.
        number = random.randint(1, 9999)
        manager_id = f"MGR{number:03d}"
        
        # Check if this ID already exists
        if not Manager.objects.filter(manager_id=manager_id).exists():
            return manager_id


def generate_employee_id():
    """Generate a unique employee ID"""
    import random
    import string
    from employe.models import Employe
    
    while True:
        # Generate ID like EMP001, EMP002, etc.
        number = random.randint(1, 9999)
        employe_id = f"EMP{number:03d}"
        
        # Check if this ID already exists
        if not Employe.objects.filter(employe_id=employe_id).exists():
            return employe_id


def get_employees_under_manager(manager):
    """Get all employees under a specific manager"""
    try:
        from employe.models import Employe
        return Employe.objects.filter(manager=manager)
    except:
        return []


def get_leave_balance_info(user):
    """Get leave balance information for a user"""
    profile = get_user_profile(user)
    if not profile:
        return None

    # Ensure counts are up to date
    profile.recalculate_leave_counts()

    current_date = timezone.now().date()
    is_cf_period = current_date.month <= 3

    return {
        'available_leaves': profile.available_leaves,
        'leaves_taken': profile.leaves_taken,
        'available_medical_leaves': profile.available_medical_leaves,
        'medical_leaves_taken': profile.medical_leaves_taken,
        'carryforward_available_leaves': profile.carryforward_available_leaves,
        'carryforward_leaves_taken': profile.carryforward_leaves_taken,
        'annual_remaining': profile.available_leaves,
        'medical_remaining': profile.available_medical_leaves,
        'total_annual_taken': profile.leaves_taken,
        'total_medical_taken': profile.medical_leaves_taken,
        'is_cf_period': is_cf_period,
        'total_available': profile.available_leaves + profile.carryforward_available_leaves if is_cf_period else profile.available_leaves
    }

from datetime import timedelta
from employe.models import Holiday

def calculate_leave_days(start_date, end_date):
    """
    Calculate the number of working days between two dates, excluding weekends and holidays.
    """
    if not start_date or not end_date:
        return 0

    if start_date > end_date:
        return 0

    # Get all holidays within the date range
    holidays = Holiday.objects.filter(date__range=[start_date, end_date]).values_list('date', flat=True)
    
    working_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Check if the day is not a weekend (Monday=0, Sunday=6) and not a holiday
        if current_date.weekday() < 5 and current_date not in holidays:
            working_days += 1
        current_date += timedelta(days=1)
        
    return working_days if working_days > 0 else 1
