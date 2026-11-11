from django import forms
from users.models import User
from .models import Employe

class EmployeAdminForm(forms.ModelForm):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep the current password.")
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    total_annual_allocated = forms.FloatField(
        required=False,
        label="Total Annual Leaves Allocated",
        help_text="Adjust total allocated annual leaves. Changing this automatically recalculates available leaves."
    )
    total_medical_allocated = forms.FloatField(
        required=False,
        label="Total Medical Leaves Allocated",
        help_text="Adjust total allocated medical leaves. Changing this automatically recalculates available medical leaves."
    )

    class Meta:
        model = Employe
        fields = '__all__'
        exclude = ('user',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if getattr(self.instance, 'user', None):
                self.fields['email'].initial = self.instance.user.email
                self.fields['first_name'].initial = self.instance.user.first_name
                self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['total_annual_allocated'].initial = self.instance.total_annual_leaves
            self.fields['total_medical_allocated'].initial = self.instance.total_medical_leaves
        else:
            self.fields['password'].required = True
            self.fields['password'].help_text = ""

    def clean(self):
        cleaned_data = super().clean()
        total_annual = cleaned_data.get('total_annual_allocated')
        taken_annual = cleaned_data.get('leaves_taken') or 0.0

        if total_annual is not None:
            initial_total = self.fields['total_annual_allocated'].initial
            if initial_total is None or abs(float(total_annual) - float(initial_total)) > 0.001:
                cleaned_data['available_leaves'] = max(0.0, float(total_annual) - float(taken_annual))

        total_med = cleaned_data.get('total_medical_allocated')
        taken_med = cleaned_data.get('medical_leaves_taken') or 0.0

        if total_med is not None:
            initial_med_total = self.fields['total_medical_allocated'].initial
            if initial_med_total is None or abs(float(total_med) - float(initial_med_total)) > 0.001:
                cleaned_data['available_medical_leaves'] = max(0.0, float(total_med) - float(taken_med))

        return cleaned_data
