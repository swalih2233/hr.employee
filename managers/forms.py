from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import ManagerLeaveRequest, UnifiedLeaveRequest, LEAVE_CHOICES
from users.models import User
from employe.models import Employe, EMPLOYE_CHOICES, STATUS_CHOICES
import re

class UnifiedLeaveRequestForm(forms.ModelForm):
    """Unified form for both employees and managers to apply for leave"""

    class Meta:
        model = UnifiedLeaveRequest
        fields = ['subject', 'leave_type', 'start_date', 'end_date', 'description', 'file']
        
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
                'placeholder': 'Enter subject for your leave application'
            }),
            'leave_type': forms.Select(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
                'placeholder': 'Provide reason for leave'
            }),
            'file': forms.FileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'
            })
        }
        
        labels = {
            'subject': 'Subject',
            'leave_type': 'Leave Type',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'description': 'Reason / Message',
            'file': 'Supporting Document (Optional)'
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("End date must be after start date.")
        
        return cleaned_data


class ManagerLeaveRequestForm(forms.ModelForm):
    """DEPRECATED: Form for managers to apply for leave - use UnifiedLeaveRequestForm instead"""

    class Meta:
        model = ManagerLeaveRequest
        fields = ['subject', 'leave_type', 'start_date', 'end_date', 'description', 'file']

        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
                'placeholder': 'Enter subject for your leave application'
            }),
            'leave_type': forms.Select(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
                'placeholder': 'Provide reason for leave'
            }),
            'file': forms.FileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'
            })
        }

        labels = {
            'subject': 'Subject',
            'leave_type': 'Leave Type',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'description': 'Reason / Message',
            'file': 'Supporting Document (Optional)'
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("End date must be after start date.")

        return cleaned_data


class AddEmployeeForm(forms.ModelForm):
    """Form for managers to add new employees under their management"""

    # User fields
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
            'placeholder': 'Enter first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
            'placeholder': 'Enter last name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
            'placeholder': 'Enter email address'
        })
    )
    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
            'placeholder': 'Enter phone number'
        })
    )

    class Meta:
        model = Employe
        fields = [
            'department', 'designation', 'date_of_joining',
            'employment_Type', 'work_location', 'employe_status', 'image'
        ]

        widgets = {
            'department': forms.TextInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
                'placeholder': 'Enter department'
            }),
            'designation': forms.TextInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
                'placeholder': 'Enter designation'
            }),
            'date_of_joining': forms.DateInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
                'type': 'date'
            }),
            'employment_Type': forms.Select(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2'
            }),
            'work_location': forms.TextInput(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2',
                'placeholder': 'Enter work location'
            }),
            'employe_status': forms.Select(attrs={
                'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2'
            }),
            'image': forms.FileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
                'accept': 'image/*'
            })
        }

        labels = {
            'department': 'Department',
            'designation': 'Designation',
            'date_of_joining': 'Date of Joining',
            'employment_Type': 'Employment Type',
            'work_location': 'Work Location',
            'employe_status': 'Employee Status',
            'image': 'Profile Picture (Optional)'
        }

    def clean_email(self):
        """Validate that email is unique"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean_phone(self):
        """Validate phone number format"""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove any non-digit characters for validation
            digits_only = re.sub(r'\D', '', phone)
            if len(digits_only) < 10:
                raise ValidationError("Phone number must be at least 10 digits.")
        return phone

    def clean_first_name(self):
        """Validate first name"""
        first_name = self.cleaned_data.get('first_name')
        if not first_name.strip():
            raise ValidationError("First name is required.")
        return first_name.strip().title()

    def clean_last_name(self):
        """Validate last name"""
        last_name = self.cleaned_data.get('last_name')
        if not last_name.strip():
            raise ValidationError("Last name is required.")
        return last_name.strip().title()

    def save(self, manager, commit=True):
        """Save the employee and create associated user"""
        if commit:
            # Create User first
            user = User.objects.create_user(
                username=self.cleaned_data['email'],  # Use email as username
                email=self.cleaned_data['email'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                phone=self.cleaned_data['phone'],
                is_employee=True,
                is_active=True
            )

            # Set a default password (should be changed on first login)
            default_password = f"{self.cleaned_data['first_name'].lower()}123"
            user.set_password(default_password)
            user.save()

            # Create Employee
            employee = super().save(commit=False)
            employee.user = user
            employee.manager = manager
            employee.reporting_manager = f"{manager.user.first_name} {manager.user.last_name}"

            if commit:
                employee.save()

            return employee, default_password

        return super().save(commit=False), None
