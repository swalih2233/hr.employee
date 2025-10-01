from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from users.models import User
from .models import Manager, Founder, UnifiedLeaveRequest

EMPLOYE_CHOICES = (
   ('FT', 'FULL TIME'),
   ('PT', 'PART TIME'),
   ('CT', 'CONTRACT'),
   ('FR', 'FREELANCE')
)

class UnifiedLeaveRequestForm(forms.ModelForm):
    class Meta:
        model = UnifiedLeaveRequest
        fields = ['subject', 'start_date', 'end_date', 'leave_type', 'description', 'file']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class AddEmployeeForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    phone_number = forms.CharField(max_length=15, required=False)
    gender = forms.ChoiceField(choices=User.GENDER_CHOICES, required=False)
    department = forms.CharField(max_length=100, required=False)
    designation = forms.CharField(max_length=100, required=False)
    date_of_joining = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    employment_Type = forms.ChoiceField(choices=EMPLOYE_CHOICES, required=False)
    work_location = forms.CharField(max_length=100, required=False)
    image = forms.ImageField(required=False)

class ManagerAdminForm(forms.ModelForm):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep the current password.")
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = Manager
        fields = '__all__'
        exclude = ('user',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
        else:
            self.fields['password'].required = True
            self.fields['password'].help_text = ""

class FounderAdminForm(forms.ModelForm):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep the current password.")
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = Founder
        fields = '__all__'
        exclude = ('user',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
        else:
            self.fields['password'].required = True
            self.fields['password'].help_text = ""