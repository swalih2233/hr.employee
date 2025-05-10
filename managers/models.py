from django.db import models

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
    department = models.CharField(max_length=100 , null=True, blank=True)
    designation = models.CharField(max_length=100 , null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    employment_Type = models.CharField(max_length=100 , choices=EMPLOYE_CHOICES, null=True, blank=True)
    reporting_manager = models.CharField(max_length=100 , null=True, blank=True)
    work_location = models.CharField(max_length=100 , null=True, blank=True)
    image = models.ImageField(upload_to='images/', null=True , blank=True)

    class Meta:
        db_table = 'manager_manager'
        verbose_name = 'manager'
        verbose_name_plural ='managers'
        ordering = ["-id"]


    def __str__(self):
        return self.user.email
     
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
