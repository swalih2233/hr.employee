from django.db import models

from common.models import CommonModel

from users.models import User


EMPLOYE_CHOICES = (
   ('FT', 'FULL TIME'),
   ('PT', 'PART TIME'),
   ('CT', 'CONTRACT'),
   ('FR', 'FREELANCE')
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

LEAVE_CHOICES =(
    ('ML', 'MEDICAL LEAVE'),
    ('PR', 'PRIVILEGE'),
    ('CA', 'CASUAL')
)

class Employe(CommonModel):
    user = models.ForeignKey(User ,on_delete=models.CASCADE)
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



class LeaveReaquest(CommonModel):
    subject = models.CharField(max_length=100)
    start_date= models.DateField(null=True, blank=True)
    end_date= models.DateField(null=True, blank=True)
    leave_type = models.CharField(max_length=100, choices=LEAVE_CHOICES, null=True, blank=True)
    description = models.CharField(max_length=200, null=True, blank=True)
    file = models.FileField(null=True, blank=True, upload_to='file')
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    approval_date = models.DateField(null=True, blank=True)  # Add approval_date field
    is_rejected = models.BooleanField(default=False)  # New
    rejection_date = models.DateField(null=True, blank=True)  # To store rejection time
    leave_duration = models.IntegerField(default=0) 
   
    class Meta:
        db_table = 'employe_leave_reaquest'
        verbose_name = 'leave_reaquest'
        verbose_name_plural ='leave_reaquests'
        ordering = ["-id"]


    def __str__(self):
        return self.employe.user.email


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