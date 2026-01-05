from django import forms
from users.models import User
from employe.models import Employe, EMPLOYE_CHOICES
from .models import Manager, Founder, UnifiedLeaveRequest

class ManagerAdminForm(forms.ModelForm):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)

    class Meta:
        model = Manager
        fields = ['department', 'designation', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

class FounderAdminForm(forms.ModelForm):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)

    class Meta:
        model = Founder
        fields = ['department', 'designation', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

class AddUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'phone_number', 'gender']

class AddEmployeModelForm(forms.ModelForm):
    class Meta:
        model = Employe
        fields = ['employe_id', 'department', 'designation', 'date_of_joining', 'employment_Type', 'work_location', 'image', 'carryforward_granted']
        widgets = {
            'date_of_joining': forms.DateInput(attrs={'type': 'date'}),
        }

class UnifiedLeaveRequestForm(forms.ModelForm):
    class Meta:
        model = UnifiedLeaveRequest
        fields = ['subject', 'start_date', 'end_date', 'leave_type', 'description', 'file']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class ManagerProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=15, required=False)
    gender = forms.ChoiceField(choices=User.GENDER_CHOICES, required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_of_joining = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Date of Joining")
    
    # Address fields
    address_permanent_address = forms.CharField(max_length=255, required=False, label="Permanent Address")
    address_city = forms.CharField(max_length=100, required=False, label="City")
    address_country = forms.CharField(max_length=100, required=False, label="Country")
    address_pincode = forms.CharField(max_length=20, required=False, label="Pincode")

    # Emergency Contact fields
    contact_permanent_address = forms.CharField(max_length=255, required=False, label="Emergency Contact Address")
    contact_country = forms.CharField(max_length=100, required=False, label="Emergency Contact Country")
    contact_city = forms.CharField(max_length=100, required=False, label="Emergency Contact City")
    contact_pincode = forms.CharField(max_length=20, required=False, label="Emergency Contact Pincode")

    # Work Schedule fields
    work_start_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'}), label="Start Time")
    work_end_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time'}), label="End Time")

    # Bank fields
    bank_name = forms.CharField(max_length=100, required=False)
    bank_account_number = forms.IntegerField(required=False, label="Account Number")
    bank_branch_name = forms.CharField(max_length=100, required=False)
    bank_ifsc_code = forms.CharField(max_length=20, required=False)

    class Meta:
        model = Manager
        fields = ['manager_id', 'designation', 'image', 'date_of_joining']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['phone_number'].initial = self.instance.user.phone_number
            self.fields['gender'].initial = self.instance.user.gender
            self.fields['date_of_birth'].initial = self.instance.user.date_of_birth
            
            # Load related model data
            from .models import AddressManager, EmergencyContactManager, BenefitsManager, WorkScheduleManager
            
            address = AddressManager.objects.filter(manager=self.instance).first()
            if address:
                self.fields['address_permanent_address'].initial = address.Permanent_address
                self.fields['address_city'].initial = address.city
                self.fields['address_country'].initial = address.country
                self.fields['address_pincode'].initial = address.pincode

            contact = EmergencyContactManager.objects.filter(manager=self.instance).first()
            if contact:
                self.fields['contact_permanent_address'].initial = contact.Permanent_address
                self.fields['contact_country'].initial = contact.country
                self.fields['contact_city'].initial = contact.city
                self.fields['contact_pincode'].initial = contact.pincode

            benefits = BenefitsManager.objects.filter(manager=self.instance).first()
            if benefits:
                self.fields['bank_name'].initial = benefits.bank_name
                self.fields['bank_account_number'].initial = benefits.account_number
                self.fields['bank_branch_name'].initial = benefits.branch_name
                self.fields['bank_ifsc_code'].initial = benefits.ifsc_code

            work = WorkScheduleManager.objects.filter(manager=self.instance).first()
            if work:
                self.fields['work_start_time'].initial = work.start_time
                self.fields['work_end_time'].initial = work.end_time
