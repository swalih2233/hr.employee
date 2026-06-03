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


def _manager_profile_for_user(user):
    from managers.models import Manager
    return Manager.objects.filter(user=user).select_related(
        'reporting_manager_profile__user', 'founder__user'
    ).first()


def sync_employee_profile_from_related(employe, save=True):
    """
    Copy missing employee fields from the same user's manager profile
    (image, ID, department, etc.) so founder assignment does not show empty rows.
    """
    manager = _manager_profile_for_user(employe.user)
    if not manager:
        return False

    updated_fields = []
    if not employe.image and manager.image:
        employe.image = manager.image
        updated_fields.append('image')
    if not employe.employe_id and manager.manager_id:
        employe.employe_id = str(manager.manager_id)
        updated_fields.append('employe_id')
    if not employe.department and manager.department:
        employe.department = manager.department
        updated_fields.append('department')
    if not employe.designation and manager.designation:
        employe.designation = manager.designation
        updated_fields.append('designation')
    if not employe.date_of_joining and manager.date_of_joining:
        employe.date_of_joining = manager.date_of_joining
        updated_fields.append('date_of_joining')
    if not employe.work_location and manager.work_location:
        employe.work_location = manager.work_location
        updated_fields.append('work_location')
    if manager.founder_id and not employe.founder_id:
        employe.founder_id = manager.founder_id
        updated_fields.append('founder')

    if save and updated_fields:
        employe.save(update_fields=updated_fields)
    return bool(updated_fields)


def get_employee_reporting_manager(employe):
    """
    Who this employee reports to: direct manager FK, previous manager,
    manager-profile reporting line, or founder if assigned under founder only.
    """
    if employe.manager_id:
        mgr = employe.manager
        return mgr.user.get_full_name() or mgr.user.email

    if employe.previous_manager_id:
        prev = employe.previous_manager
        return prev.user.get_full_name() or prev.user.email

    manager_profile = _manager_profile_for_user(employe.user)
    if manager_profile and manager_profile.reporting_manager_profile_id:
        rm = manager_profile.reporting_manager_profile
        return rm.user.get_full_name() or rm.user.email

    if employe.founder_id:
        founder_user = employe.founder.user
        return founder_user.get_full_name() or founder_user.email

    if manager_profile and manager_profile.founder_id:
        founder_user = manager_profile.founder.user
        return founder_user.get_full_name() or founder_user.email

    return None


def get_employee_display_department(employe):
    """Department / role label for tables when employe.department is empty."""
    if employe.department:
        return employe.department
    if employe.designation:
        return employe.designation

    manager_profile = _manager_profile_for_user(employe.user)
    if manager_profile:
        if manager_profile.department:
            return manager_profile.department
        if manager_profile.designation:
            return manager_profile.designation

    if employe.founder_id:
        founder = employe.founder
        if founder.department:
            return founder.department
        if founder.designation:
            return founder.designation

    if employe.manager_id and employe.manager.department:
        return employe.manager.department

    return None


def get_employee_display_profile(employe):
    """Resolved avatar, ID, department, and reporting manager for UI display."""
    manager_profile = _manager_profile_for_user(employe.user)

    image = employe.image or (manager_profile.image if manager_profile else None)
    display_id = employe.employe_id or (
        str(manager_profile.manager_id) if manager_profile and manager_profile.manager_id else None
    )
    display_dept = get_employee_display_department(employe)
    display_manager = get_employee_reporting_manager(employe)

    image_url = image.url if image else None
    user = employe.user
    initials = (
        f"{(user.first_name or '?')[0]}{(user.last_name or '?')[0]}".upper()
    )

    return {
        'image_url': image_url,
        'initials': initials,
        'display_id': display_id,
        'display_dept': display_dept,
        'display_manager': display_manager,
    }


def build_founder_employee_table_rows(employes):
    """
    Build display rows for the founder dashboard employee table.
    Employees only — managers belong in the Managers List section.
    """
    rows = []
    seen_user_ids = set()
    for emp in employes:
        if emp.user_id in seen_user_ids:
            continue
        seen_user_ids.add(emp.user_id)
        display = get_employee_display_profile(emp)
        rows.append({
            'profile': emp,
            'is_manager': False,
            'display_id': display['display_id'],
            'display_dept': display['display_dept'],
            'display_manager': display['display_manager'],
            'display_image_url': display['image_url'],
            'display_initials': display['initials'],
        })
    return rows


def get_employees_under_manager(manager):
    """Get all employees and sub-managers under a specific manager"""
    try:
        from employe.models import Employe
        from managers.models import Manager
        
        # Get standard employees
        employees = list(Employe.objects.filter(manager=manager))
        
        # Get managers reporting to this manager
        sub_managers = list(Manager.objects.filter(reporting_manager_profile=manager))
        
        # Return combined list
        return employees + sub_managers
    except Exception as e:
        print(f"Error in get_employees_under_manager: {e}")
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

HALF_DAY_SESSION_INFO = {
    'AM': {'label': 'Morning', 'time': '9:00 AM – 1:00 PM'},
    'PM': {'label': 'Afternoon', 'time': '1:00 PM – 6:00 PM'},
}


def get_user_display_name(user):
    """Full name for display; fallback to email if name is empty."""
    if user is None:
        return None
    full = (user.get_full_name() or '').strip()
    if full:
        return full
    parts = [(user.first_name or '').strip(), (user.last_name or '').strip()]
    name = ' '.join(p for p in parts if p)
    return name or user.email


def get_half_day_info(leave):
    """Return session label and time range for half-day leave, or None."""
    if not getattr(leave, 'is_half_day', False):
        return None
    return HALF_DAY_SESSION_INFO.get(
        getattr(leave, 'half_day_session', None),
        {'label': 'Half-day', 'time': '9:00 AM – 6:00 PM'},
    )


def format_leave_duration_display(leave):
    """Human-readable duration for emails and UI."""
    if getattr(leave, 'is_half_day', False):
        info = get_half_day_info(leave)
        return f"Half day — {info['label']} ({info['time']})"
    duration = float(getattr(leave, 'leave_duration', 0) or 0)
    if duration == int(duration):
        count = int(duration)
        return f"{count} Day{'s' if count != 1 else ''}"
    return f"{duration} Day{'s' if duration != 1 else ''}"


def calculate_leave_days(start_date, end_date, is_half_day=False):
    """
    Calculate working days between two dates (Mon–Fri, excluding holidays).
    Half-day leave (9am–6pm) counts as 0.5 for a single working day.
    """
    if not start_date or not end_date:
        return 0

    if start_date > end_date:
        return 0

    holidays = Holiday.objects.filter(date__range=[start_date, end_date]).values_list('date', flat=True)

    working_days = 0
    current_date = start_date

    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in holidays:
            working_days += 1
        current_date += timedelta(days=1)

    if is_half_day:
        return 0.5 if working_days > 0 else 0
    return float(working_days)
