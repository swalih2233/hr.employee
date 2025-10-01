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
        fields = ['employe_id', 'department', 'designation', 'date_of_joining', 'employment_Type', 'work_location', 'image']
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
