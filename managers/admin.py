from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import *


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = [
        'user_name', 'manager_id', 'department', 'designation',
        'available_leaves', 'leaves_taken', 'carryforward_available_leaves',
        'available_medical_leaves', 'medical_leaves_taken', 'date_of_joining'
    ]
    list_filter = ['department', 'designation', 'employment_Type', 'date_of_joining']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'manager_id', 'department']
    readonly_fields = ['created_date']

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'manager_id', 'department', 'designation', 'date_of_joining')
        }),
        ('Employment Details', {
            'fields': ('employment_Type', 'reporting_manager', 'work_location', 'image')
        }),
        ('Leave Management', {
            'fields': (
                'available_leaves', 'leaves_taken',
                'available_medical_leaves', 'medical_leaves_taken',
                'carryforward_available_leaves', 'carryforward_leaves_taken'
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_date',),
            'classes': ('collapse',)
        }),
    )

    def user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_name.short_description = 'Name'
    user_name.admin_order_field = 'user__first_name'

    actions = ['reset_annual_leaves', 'reset_carryforward_leaves']

    def reset_annual_leaves(self, request, queryset):
        updated = queryset.update(
            available_leaves=18,
            leaves_taken=0,
            available_medical_leaves=14,
            medical_leaves_taken=0
        )
        self.message_user(request, f'{updated} managers had their annual leaves reset.')
    reset_annual_leaves.short_description = "Reset annual leaves to default"

    def reset_carryforward_leaves(self, request, queryset):
        updated = queryset.update(
            carryforward_available_leaves=0,
            carryforward_leaves_taken=0
        )
        self.message_user(request, f'{updated} managers had their carryforward leaves reset.')
    reset_carryforward_leaves.short_description = "Reset carryforward leaves to zero"


@admin.register(Founder)
class FounderAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'user_email', 'created_date']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    readonly_fields = ['created_date']

    def user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    user_name.short_description = 'Name'
    user_name.admin_order_field = 'user__first_name'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'


try:
    admin.site.register(UnifiedLeaveRequest)
except:
    pass

try:
    admin.site.register(ManagerLeaveRequest)
except:
    pass

admin.site.register(EmergencyContactManager)
admin.site.register(AddressManager)
admin.site.register(BackgroundManager)
admin.site.register(BenefitsManager)
admin.site.register(SkillManager)
admin.site.register(IdentificationManager)
admin.site.register(WorkScheduleManager)

