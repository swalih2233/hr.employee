from django.contrib import admin
from django import forms
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from .models import Manager, Founder
from .forms import ManagerAdminForm, FounderAdminForm
from users.models import User
from employe.models import Employe
from common.utils import sync_employee_profile_from_related

class EmployeInlineForm(forms.ModelForm):
    class Meta:
        model = Employe
        fields = ('user',)

    def validate_unique(self):
        # Skip uniqueness validation for user if we are going to handle it in save
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            # If the error is only about the 'user' field being unique, ignore it
            # this allows us to re-assign existing employees
            if 'user' in e.error_dict and len(e.error_dict) == 1:
                pass
            else:
                raise

class EmployeInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        user = form.cleaned_data.get('user')
        # Check if an Employe already exists for this user
        existing = Employe.objects.filter(user=user).first()
        if existing:
            # Update existing employee with new manager
            if existing.manager and existing.manager != self.instance:
                existing.previous_manager = existing.manager
            existing.manager = self.instance
            if commit:
                existing.save()
            return existing
        
        # If not existing, create new one as usual
        instance = super().save_new(form, commit=False)
        instance.manager = self.instance
        if commit:
            instance.save()
        return instance

    def delete_existing(self, obj, commit=True):
        """Instead of deleting the employee, revert to previous manager or set to None"""
        if commit:
            if obj.previous_manager:
                # Restore to previous manager
                obj.manager = obj.previous_manager
                obj.previous_manager = None
                obj.save()
            else:
                # No previous manager — keep manager as-is, don't wipe it
                # Only clear if it was explicitly assigned via this inline
                pass  # Do NOT set manager=None; preserve existing assignment

class EmployeInline(admin.TabularInline):
    model = Employe
    form = EmployeInlineForm
    formset = EmployeInlineFormSet
    extra = 1
    fields = ('user',)
    fk_name = 'manager'


# --- Founder inline: assign employees directly under founder ---
class FounderEmployeInlineForm(forms.ModelForm):
    class Meta:
        model = Employe
        fields = ('user',)

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            if 'user' in e.error_dict and len(e.error_dict) == 1:
                pass
            else:
                raise

class FounderEmployeInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        user = form.cleaned_data.get('user')
        existing = Employe.objects.filter(user=user).first()
        if existing:
            if existing.manager and existing.manager != self.instance:
                existing.previous_manager = existing.manager
            existing.founder = self.instance
            # Link reporting manager when employee has no direct manager yet
            if not existing.manager_id:
                from managers.models import Manager
                mgr_profile = Manager.objects.filter(user=user).first()
                if mgr_profile and mgr_profile.reporting_manager_profile_id:
                    existing.manager = mgr_profile.reporting_manager_profile
            sync_employee_profile_from_related(existing, save=False)
            if commit:
                existing.save()
            return existing

        instance = super().save_new(form, commit=False)
        instance.founder = self.instance
        sync_employee_profile_from_related(instance, save=False)
        if commit:
            instance.save()
        return instance

    def delete_existing(self, obj, commit=True):
        """When removed from founder, restore to previous manager if available"""
        if commit:
            if obj.previous_manager:
                obj.manager = obj.previous_manager
                obj.previous_manager = None
                obj.founder = None
                obj.save()
            else:
                # Don't wipe founder blindly — only clear if no previous manager
                obj.founder = None
                obj.save()

class FounderEmployeInline(admin.TabularInline):
    model = Employe
    form = FounderEmployeInlineForm
    formset = FounderEmployeInlineFormSet
    extra = 1
    fields = ('user',)
    fk_name = 'founder'
    verbose_name = "Employee Under Founder"
    verbose_name_plural = "Employees Under Founder"

class ManagerInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        user = form.cleaned_data.get('user')
        # Check if a Manager already exists for this user
        existing = Manager.objects.filter(user=user).first()
        if existing:
            # Update existing manager with new reporting manager
            if existing.reporting_manager_profile and existing.reporting_manager_profile != self.instance:
                existing.previous_reporting_manager = existing.reporting_manager_profile
            existing.reporting_manager_profile = self.instance
            if commit:
                existing.save()
            return existing

        instance = super().save_new(form, commit=False)
        instance.reporting_manager_profile = self.instance
        if commit:
            instance.save()
        return instance

    def delete_existing(self, obj, commit=True):
        """Instead of deleting the manager record, revert to previous reporting manager or set to None"""
        if commit:
            if obj.previous_reporting_manager:
                obj.reporting_manager_profile = obj.previous_reporting_manager
                obj.previous_reporting_manager = None
                obj.save()
            else:
                obj.reporting_manager_profile = None
                obj.save()

class ManagerInline(admin.TabularInline):
    model = Manager
    formset = ManagerInlineFormSet
    extra = 1
    fields = ('user',)
    fk_name = 'reporting_manager_profile'
    verbose_name = "Sub-Manager"
    verbose_name_plural = "Sub-Managers"

class ManagerAdmin(admin.ModelAdmin):
    form = ManagerAdminForm
    inlines = [EmployeInline, ManagerInline]
    list_display = ('get_email', 'department', 'designation', 'available_leaves', 'available_medical_leaves', 'carryforward_available_leaves')
    search_fields = ('user__email', 'department')
    fieldsets = (
        ('Personal Info', {
            'fields': ('email', 'password', 'first_name', 'last_name', 'image')
        }),
        ('Professional Info', {
            'fields': ('department', 'designation', 'manager_id', 'founder', 'date_of_joining', 'employment_Type', 'reporting_manager', 'work_location')
        }),
        ('Leave Management', {
            'fields': (
                'available_leaves', 'leaves_taken',
                'available_medical_leaves', 'medical_leaves_taken',
                'carryforward_available_leaves', 'carryforward_leaves_taken', 'carryforward_granted'
            )
        }),
    )

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def save_model(self, request, obj, form, change):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')

        if change:
            user = obj.user
            user.email = email
            user.username = email
            user.first_name = first_name
            user.last_name = last_name
            if password:
                user.set_password(password)
            user.save()
        else:
            user = User.objects.create_user(username=email, email=email, password=password, first_name=first_name, last_name=last_name, is_manager=True, is_employee=False)
            obj.user = user
        
        super().save_model(request, obj, form, change)

class FounderAdmin(admin.ModelAdmin):
    form = FounderAdminForm
    inlines = [FounderEmployeInline]
    list_display = ('get_email', 'department', 'designation')
    search_fields = ('user__email', 'department')

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def save_model(self, request, obj, form, change):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')

        if change:
            user = obj.user
            user.email = email
            user.username = email
            user.first_name = first_name
            user.last_name = last_name
            if password:
                user.set_password(password)
            user.save()
        else:
            user = User.objects.create_user(username=email, email=email, password=password, first_name=first_name, last_name=last_name, is_manager=True, is_employee=False)
            obj.user = user
        
        super().save_model(request, obj, form, change)

admin.site.register(Manager, ManagerAdmin)
admin.site.register(Founder, FounderAdmin)
