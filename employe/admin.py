from django.contrib import admin
from django.utils.html import format_html
from .models import Employe
from .forms import EmployeAdminForm
from users.models import User

class EmployeAdmin(admin.ModelAdmin):
    form = EmployeAdminForm
    list_display = ('get_email', 'department', 'designation', 'get_manager_display', 'available_leaves', 'available_medical_leaves', 'carryforward_available_leaves')
    list_filter = ('manager', 'department', 'employe_status')
    search_fields = ('user__email', 'department')
    fieldsets = (
        ('Personal Info', {
            'fields': ('email', 'password', 'first_name', 'last_name', 'image')
        }),
        ('Professional Info', {
            'fields': ('employe_id', 'department', 'designation', 'manager', 'previous_manager', 'founder', 'date_of_joining', 'employment_Type', 'reporting_manager', 'work_location', 'employe_status')
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

    def get_manager_display(self, obj):
        if obj.manager:
            return obj.manager.user.get_full_name() or obj.manager.user.email
        # Highlight employees with no manager so admin can easily spot and fix them
        if obj.previous_manager:
            return format_html(
                '<span style="color:orange;font-weight:bold;">⚠ No Manager (Previous: {})</span>',
                obj.previous_manager.user.get_full_name() or obj.previous_manager.user.email
            )
        return format_html('<span style="color:red;font-weight:bold;">⚠ No Manager Assigned</span>')
    get_manager_display.short_description = 'Manager'

    def save_model(self, request, obj, form, change):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')

        if change:
            # Track manager change — preserve previous manager so it can be restored
            old_obj = Employe.objects.get(pk=obj.pk)
            if old_obj.manager != obj.manager:
                obj.previous_manager = old_obj.manager

            user = obj.user
            user.email = email
            user.username = email
            user.first_name = first_name
            user.last_name = last_name
            if password:
                user.set_password(password)
            user.save()
        else:
            user = User.objects.create_user(username=email, email=email, password=password, first_name=first_name, last_name=last_name, is_employee=True, is_manager=False)
            obj.user = user
        
        super().save_model(request, obj, form, change)

admin.site.register(Employe, EmployeAdmin)
