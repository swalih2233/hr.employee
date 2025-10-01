from django.db import models
from datetime import datetime, timedelta

from common.models import CommonModel

from users.models import User


EMPLOYE_CHOICES = (

   ('FT', 'FULL TIME'),
   ('PT', 'PART TIME'),
   ('CT', 'CONTRACT'),
   ('FR', 'FREELANCE')
)

ID_CHOICES = (
    ('AD', 'ADHAAR'),
    ('PS', 'PASSPORT'),
    ('SSN', ' SOCIAL SECURITY NUMBER (US)' )
)


class Manager(CommonModel):
    user = models.ForeignKey(User ,on_delete=models.CASCADE)
    manager_id = models.CharField(max_length=20, unique=True, null=True, blank=True)  # New manager ID field
    department = models.CharField(max_length=100 , null=True, blank=True)
    designation = models.CharField(max_length=100 , null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    employment_Type = models.CharField(max_length=100 , choices=EMPLOYE_CHOICES, null=True, blank=True)
    reporting_manager = models.CharField(max_length=100 , null=True, blank=True)
    work_location = models.CharField(max_length=100 , null=True, blank=True)
    image = models.ImageField(upload_to='images/', null=True , blank=True)

    # Leave management fields for managers
    available_leaves = models.IntegerField(default=18)
    leaves_taken = models.IntegerField(default=0)
    medical_leaves_taken = models.IntegerField(default=0)
    available_medical_leaves = models.IntegerField(default=14)
    carryforward_leaves_taken = models.IntegerField(default=0)
    carryforward_available_leaves = models.IntegerField(default=0)

    class Meta:
        db_table = 'manager_manager'
        verbose_name = 'manager'
        verbose_name_plural ='managers'
        ordering = ["-id"]


    def __str__(self):
        return self.user.email

class Founder(CommonModel):
    user = models.ForeignKey(User ,on_delete=models.CASCADE)
    department = models.CharField(max_length=100 , null=True, blank=True)
    designation = models.CharField(max_length=100 , null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    employment_Type = models.CharField(max_length=100 , choices=EMPLOYE_CHOICES, null=True, blank=True)
    reporting_manager = models.CharField(max_length=100 , null=True, blank=True)
    work_location = models.CharField(max_length=100 , null=True, blank=True)
    image = models.ImageField(upload_to='founder_images/', null=True , blank=True)

    class Meta:
        db_table = 'manager_founder'
        verbose_name = 'founder'
        verbose_name_plural ='founders'
        ordering = ["-id"]


    def __str__(self):
        return self.user.email


LEAVE_CHOICES = (
    ('ML', 'Medical Leave'),
    ('AL', 'Annual Leave'),
)

ROLE_CHOICES = (
    ('employee', 'Employee'),
    ('manager', 'Manager'),
)

class UnifiedLeaveRequest(CommonModel):
    """Unified leave request model for both employees and managers"""
    subject = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    leave_type = models.CharField(max_length=100, choices=LEAVE_CHOICES, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    file = models.FileField(null=True, blank=True, upload_to='leave_files')

    # Role-based requester
    requested_by_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')

    # Foreign keys for different types of requesters
    employee = models.ForeignKey('employe.Employe', on_delete=models.CASCADE, null=True, blank=True, related_name='unified_leave_requests')
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE, null=True, blank=True, related_name='unified_leave_requests')

    # Approval fields
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_unified_leaves')
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_unified_leaves')

    # Leave calculation
    leave_duration = models.IntegerField(default=0)

    class Meta:
        db_table = 'unified_leave_request'
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'
        ordering = ["-id"]

    def calculate_working_days(self):
        """Calculate working days between start_date and end_date (excluding weekends)"""
        if not self.start_date or not self.end_date:
            return 0

        # Convert string dates to date objects if needed
        start_date = self.start_date
        end_date = self.end_date

        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Ensure start_date is not after end_date
        if start_date > end_date:
            return 0

        # Count working days (Monday=0, Sunday=6)
        working_days = 0
        current_date = start_date

        while current_date <= end_date:
            # Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
            if current_date.weekday() < 5:  # Monday to Friday
                working_days += 1
            current_date += timedelta(days=1)

        return working_days

    def save(self, *args, **kwargs):
        """Override save to automatically calculate leave duration"""
        # Calculate working days before saving
        self.leave_duration = self.calculate_working_days()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.requested_by_role == 'manager' and self.manager:
            return f"Manager: {self.manager.user.email} - {self.subject}"
        elif self.requested_by_role == 'employee' and self.employee:
            return f"Employee: {self.employee.user.email} - {self.subject}"
        return f"Leave Request: {self.subject}"

    @property
    def status(self):
        if self.is_approved:
            return "Approved"
        elif self.is_rejected:
            return "Rejected"
        else:
            return "Pending"

    @property
    def requester(self):
        """Get the actual requester object"""
        if self.requested_by_role == 'manager':
            return self.manager
        elif self.requested_by_role == 'employee':
            return self.employee
        return None

    @property
    def requester_name(self):
        """Get the requester's full name"""
        requester = self.requester
        if requester:
            return f"{requester.user.first_name} {requester.user.last_name}"
        return "Unknown"

    @property
    def requester_email(self):
        """Get the requester's email"""
        requester = self.requester
        if requester:
            return requester.user.email
        return "Unknown"


# Keep the old ManagerLeaveRequest for backward compatibility (will be deprecated)
class ManagerLeaveRequest(CommonModel):
    """DEPRECATED: Use UnifiedLeaveRequest instead"""
    subject = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    leave_type = models.CharField(max_length=100, choices=LEAVE_CHOICES, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    file = models.FileField(null=True, blank=True, upload_to='manager_leave_files')

    # Manager who requested the leave
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE, related_name='old_leave_requests')

    # Approval fields
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_old_manager_leaves')
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_old_manager_leaves')

    # Leave calculation
    leave_duration = models.IntegerField(default=0)

    class Meta:
        db_table = 'manager_leave_request'
        verbose_name = 'Manager Leave Request (Old)'
        verbose_name_plural = 'Manager Leave Requests (Old)'
        ordering = ["-id"]

    def __str__(self):
        return f"{self.manager.user.email} - {self.subject}"

class EmergencyContactManager(CommonModel):
    manager = models.ForeignKey(Manager ,on_delete=models.CASCADE )
    Permanent_address = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100,  null=True, blank=True)
    city = models.CharField(max_length=100,  null=True, blank=True)
    pincode = models.CharField(max_length=100,  null=True, blank=True) 
    
    class Meta:
        db_table = 'manager_contact'
        verbose_name = 'contact'
        verbose_name_plural ='contacts'
        ordering = ["-id"]


    def __str__(self):
        return self.manager.user.email


class AddressManager(CommonModel):
    manager = models.ForeignKey(Manager ,on_delete=models.CASCADE )
    Permanent_address = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=100, null=True, blank=True) 


    class Meta:
        db_table = 'manager_address'
        verbose_name = 'address'
        verbose_name_plural ='address'
        ordering = ["-id"]


    def __str__(self):
        return self.manager.user.email
    

class BenefitsManager(CommonModel):
    manager = models.ForeignKey(Manager ,on_delete=models.CASCADE )
    salary_details = models.CharField(max_length=100, null=True, blank=True) 
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.IntegerField(null=True, blank=True)
    branch_name = models.CharField(max_length=100, null=True, blank=True)
    ifsc_code = models.CharField(max_length=100, null=True, blank=True)
    pancard = models.CharField(max_length=100, null=True, blank=True)
    pancard_file = models.FileField(max_length=100, null=True, blank=True)
    pf_fund = models.FloatField(default=0)
    state_insurance_number = models.CharField(max_length=100, null=True, blank=True)


 
    class Meta:
        db_table = 'manager_benefits'
        verbose_name = 'benefits'
        verbose_name_plural ='benefit'
        ordering = ["-id"]


    def __str__(self):
        return self.manager.user.email
    

class BackgroundManager(CommonModel):
    manager = models.ForeignKey(Manager ,on_delete=models.CASCADE )
    educational_qualifications = models.CharField(max_length=100, null=True, blank=True)
    previous_details =models.CharField(max_length=100, null=True, blank=True)


    class Meta:
        db_table = 'manager_background'
        verbose_name = 'background'
        verbose_name_plural ='backgrounds'
        ordering = ["-id"]


    def __str__(self):
        return self.manager.user.email

class SkillManager(CommonModel):
    skill = models.CharField()


    class Meta:
        db_table = 'manager_ skill'
        verbose_name = ' skill'
        verbose_name_plural =' skills'
        ordering = ["-id"]


    def __str__(self):
        return self.skill
    



class IdentificationManager(CommonModel):
    manager = models.ForeignKey(Manager ,on_delete=models.CASCADE )
    employe_type = models.CharField(max_length=100, choices=ID_CHOICES, null=True, blank=True)  
    work_authorization = models.CharField(max_length=100, null=True, blank=True)
    skill = models.ManyToManyField(SkillManager)

    class Meta:
        db_table = 'manager_work_schedule'
        verbose_name = 'work_schedule'
        verbose_name_plural ='work_schedules'
        ordering = ["-id"]


    def __str__(self):
        return self.manager.user.email
    

class WorkScheduleManager(CommonModel):
    manager = models.ForeignKey(Manager ,on_delete=models.CASCADE)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)    


    class Meta:
        db_table = 'manager_Identification'
        verbose_name = 'Identification'
        verbose_name_plural ='Identificationss'
        ordering = ["-id"]


    def __str__(self):
        return self.manager.user.email
