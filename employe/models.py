from django.db import models
from datetime import datetime, timedelta

from common.models import CommonModel

from users.models import User
from managers.models import Manager

EMPLOYE_CHOICES = (
    ('Full-Time', 'Full-Time'),
    ('Part-Time', 'Part-Time'),
    ('Contract', 'Contract'),
    ('Internship', 'Internship'),
)

STATUS_CHOICES = (
    ('AT', 'ACTIVE'),
    ('PR', 'PROBATION'),
    ('LE', 'LEAVE')
)

ID_CHOICES = (

    ('AD', 'ADHAAR'),
    ('PS', 'PASSPORT'),
    ('SSN', ' SOCIAL SECURITY NUMBER (US)' )

)

LEAVE_CHOICES = (
    ('ML', 'Medical Leave'),
    ('AL', 'Annual Leave'),  
)

class Employe(CommonModel):
    user = models.ForeignKey(User ,on_delete=models.CASCADE)
    employe_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    manager =models.ForeignKey(Manager, on_delete=models.CASCADE, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    designation = models.CharField(max_length=100, null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    employment_Type = models.CharField(max_length=100, choices=EMPLOYE_CHOICES, null=True, blank=True)
    reporting_manager = models.CharField(max_length=100, null=True, blank=True)
    work_location = models.CharField(max_length=100, null=True, blank=True)
    employe_status = models.CharField(max_length=100, choices=STATUS_CHOICES, null=True, blank=True)
    image = models.ImageField(upload_to='images/', null=True , blank=True)
    available_leaves = models.IntegerField(default=18)  
    leaves_taken = models.IntegerField(default=0)
    medical_leaves_taken = models.IntegerField(default=0)
    available_medical_leaves = models.IntegerField(default=14)
    carryforward_leaves_taken = models.IntegerField(default=0)
    carryforward_available_leaves = models.IntegerField(default=0)

    class Meta:
        db_table = 'employe_employe'
        verbose_name = 'employe'
        verbose_name_plural ='employes'
        ordering = ["-id"]


    def __str__(self):
        return self.user.email
     
class EmergencyContact(CommonModel):
    employe = models.ForeignKey(Employe ,on_delete=models.CASCADE )
    contact_name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=100, null=True, blank=True)
    relationship = models.CharField(max_length=100, null=True, blank=True)
    permanent_address = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100,  null=True, blank=True)
    city = models.CharField(max_length=100,  null=True, blank=True)
    pincode = models.CharField(max_length=100,  null=True, blank=True) 
    
    class Meta:
        db_table = 'employe_contact'
        verbose_name = 'contact'
        verbose_name_plural ='contacts'
        ordering = ["-id"]


    def __str__(self):
        return self.employe.user.email


class Address(CommonModel):
    employe = models.ForeignKey(Employe ,on_delete=models.CASCADE )
    permanent_address = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=100, null=True, blank=True) 


    class Meta:
        db_table = 'employe_address'
        verbose_name = 'address'
        verbose_name_plural ='address'
        ordering = ["-id"]


    def __str__(self):
        return self.employe.user.email
    

class Benefits(CommonModel):
    employe = models.ForeignKey(Employe ,on_delete=models.CASCADE )
    salary_details = models.CharField(max_length=100, null=True, blank=True) 
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.IntegerField(null=True, blank=True)
    branch_name = models.CharField(max_length=100, null=True, blank=True)
    ifsc_code = models.CharField(max_length=100, null=True, blank=True)
    pancard = models.CharField(max_length=100, null=True, blank=True)
    pancard_file = models.FileField(max_length=100, null=True, blank=True, upload_to='pancard')
    pf_fund = models.FloatField(default=0)
    state_insurance_number = models.CharField(max_length=100, null=True, blank=True)


 
    class Meta:
        db_table = 'employe_benefits'
        verbose_name = 'benefits'
        verbose_name_plural ='benefit'
        ordering = ["-id"]


    def __str__(self):
        return self.employe.user.email
    

class Background(CommonModel):
    employe = models.ForeignKey(Employe ,on_delete=models.CASCADE )
    educational_qualifications = models.CharField(max_length=100, null=True, blank=True)
    previous_details =models.CharField(max_length=100, null=True, blank=True)


    class Meta:
        db_table = 'employe_background'
        verbose_name = 'background'
        verbose_name_plural ='backgrounds'
        ordering = ["-id"]


    def __str__(self):
        return self.employe.user.email

class Skill(CommonModel):
    title = models.CharField(max_length=500)


    class Meta:
        db_table = 'employe_skill'
        verbose_name = ' skill'
        verbose_name_plural =' skills'
        ordering = ["-id"]


    def __str__(self):
        return self.title
    



class Identification(CommonModel):
    employe = models.ForeignKey(Employe ,on_delete=models.CASCADE )
    employe_type = models.CharField(max_length=100, choices=ID_CHOICES, null=True, blank=True)  
    work_authorization = models.CharField(max_length=100, null=True, blank=True)
    skills = models.CharField(max_length=500, null=True,blank=True)

    class Meta:
        db_table = 'employe_identification'
        verbose_name = 'identification'
        verbose_name_plural ='identifications'
        ordering = ["-id"]


    def __str__(self):
        return self.employe.user.email
    

class WorkSchedule(CommonModel):
    employe = models.ForeignKey(Employe ,on_delete=models.CASCADE)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)    


    class Meta:
        db_table = 'employe_workSchedule'
        verbose_name = 'workSchedule'
        verbose_name_plural ='workSchedules'
        ordering = ["-id"]


    def __str__(self):
        return self.employe.user.email



# Fixed: Corrected model name from LeaveReaquest to LeaveRequest and added status field
class LeaveRequest(CommonModel):
    subject = models.CharField(max_length=100)
    start_date= models.DateField(null=True, blank=True)
    end_date= models.DateField(null=True, blank=True)
    leave_type = models.CharField(max_length=100, choices=LEAVE_CHOICES, null=True, blank=True)
    description = models.CharField(max_length=200, null=True, blank=True)
    file = models.FileField(null=True, blank=True, upload_to='file')
    employee = models.ForeignKey(User, on_delete=models.CASCADE)  # Fixed: Changed to User model and renamed field
    status = models.CharField(max_length=20, default='Pending', choices=[
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected')
    ])  # Fixed: Added status field as required
    is_approved = models.BooleanField(default=False)
    approval_date = models.DateField(null=True, blank=True)
    is_rejected = models.BooleanField(default=False)
    rejection_date = models.DateField(null=True, blank=True)
    leave_duration = models.IntegerField(default=0)

    class Meta:
        db_table = 'employe_leave_request'  # Fixed: Corrected table name
        verbose_name = 'leave_request'  # Fixed: Corrected verbose name
        verbose_name_plural ='leave_requests'  # Fixed: Corrected plural name
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
        return f"{self.employee.email} - {self.subject}"  # Fixed: Updated to use employee field


class Leave(models.Model):
    employe = models.OneToOneField(Employe, on_delete=models.CASCADE)
    total_leaves = models.IntegerField(default=18)  
    leaves_taken = models.IntegerField(default=0)  


    class Meta:
        db_table = 'employe_leave'
        verbose_name = 'leave'
        verbose_name_plural ='leaves'
        ordering = ["-id"]


    def __str__(self):
        return self.employe.user.email
    

class Holiday(CommonModel):
    title = models.CharField(max_length=250)
    date = models.DateField(null=True, blank=True)


    class Meta:
        db_table = 'employe_holiday'
        verbose_name = 'holiday'
        verbose_name_plural ='holidays'
        ordering = ["-id"]


    def __str__(self):
        return self.title
