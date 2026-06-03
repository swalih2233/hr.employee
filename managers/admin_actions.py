"""
Django Admin Actions for Carryforward Leave Management

Add these actions to your Django admin to manually trigger carryforward processes.
"""

from django.contrib import admin
from django.contrib import messages
from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html
from io import StringIO
import logging

logger = logging.getLogger(__name__)


class CarryforwardAdminMixin:
    """
    Mixin to add carryforward management actions to Django admin
    """
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('carryforward-grant/', self.admin_site.admin_view(self.carryforward_grant_view), 
                 name='carryforward_grant'),
            path('carryforward-cleanup/', self.admin_site.admin_view(self.carryforward_cleanup_view), 
                 name='carryforward_cleanup'),
            path('carryforward-test/', self.admin_site.admin_view(self.carryforward_test_view), 
                 name='carryforward_test'),
        ]
        return custom_urls + urls
    
    def carryforward_grant_view(self, request):
        """Admin view to grant carryforward leaves"""
        if request.method == 'POST':
            try:
                # Capture command output
                out = StringIO()
                call_command('process_carryforward_leaves', action='grant', stdout=out)
                output = out.getvalue()
                
                messages.success(request, "Carryforward leaves granted successfully!")
                
                context = {
                    'title': 'Carryforward Grant Results',
                    'output': output,
                    'action': 'grant'
                }
                return render(request, 'admin/carryforward_result.html', context)
                
            except Exception as e:
                messages.error(request, f"Error granting carryforward leaves: {e}")
                logger.error(f"Admin carryforward grant failed: {e}")
        
        context = {
            'title': 'Grant Carryforward Leaves',
            'action': 'grant',
            'description': 'Grant 6 carryforward leaves to employees who have taken 10+ leaves.',
            'warning': 'This will modify employee leave balances. Use with caution!'
        }
        return render(request, 'admin/carryforward_confirm.html', context)
    
    def carryforward_cleanup_view(self, request):
        """Admin view to cleanup carryforward leaves"""
        if request.method == 'POST':
            try:
                # Capture command output
                out = StringIO()
                call_command('process_carryforward_leaves', action='cleanup', stdout=out)
                output = out.getvalue()
                
                messages.success(request, "Carryforward cleanup completed successfully!")
                
                context = {
                    'title': 'Carryforward Cleanup Results',
                    'output': output,
                    'action': 'cleanup'
                }
                return render(request, 'admin/carryforward_result.html', context)
                
            except Exception as e:
                messages.error(request, f"Error during carryforward cleanup: {e}")
                logger.error(f"Admin carryforward cleanup failed: {e}")
        
        context = {
            'title': 'Cleanup Carryforward Leaves',
            'action': 'cleanup',
            'description': 'Remove all unused carryforward leaves (typically run on March 31st).',
            'warning': 'This will remove unused carryforward leaves permanently!'
        }
        return render(request, 'admin/carryforward_confirm.html', context)
    
    def carryforward_test_view(self, request):
        """Admin view to test carryforward system"""
        try:
            # Capture command output
            out = StringIO()
            call_command('process_carryforward_leaves', action='test', dry_run=True, stdout=out)
            output = out.getvalue()
            
            context = {
                'title': 'Carryforward System Test Results',
                'output': output,
                'action': 'test'
            }
            return render(request, 'admin/carryforward_result.html', context)
            
        except Exception as e:
            messages.error(request, f"Error testing carryforward system: {e}")
            logger.error(f"Admin carryforward test failed: {e}")
            
            context = {
                'title': 'Carryforward System Test',
                'error': str(e)
            }
            return render(request, 'admin/carryforward_error.html', context)


def carryforward_grant_action(modeladmin, request, queryset):
    """Admin action to grant carryforward leaves"""
    try:
        call_command('process_carryforward_leaves', action='grant')
        messages.success(request, "Carryforward leaves granted successfully!")
    except Exception as e:
        messages.error(request, f"Error granting carryforward leaves: {e}")

carryforward_grant_action.short_description = "Grant carryforward leaves to eligible employees"


def carryforward_cleanup_action(modeladmin, request, queryset):
    """Admin action to cleanup carryforward leaves"""
    try:
        call_command('process_carryforward_leaves', action='cleanup')
        messages.success(request, "Carryforward cleanup completed successfully!")
    except Exception as e:
        messages.error(request, f"Error during carryforward cleanup: {e}")

carryforward_cleanup_action.short_description = "Cleanup unused carryforward leaves"


def carryforward_test_action(modeladmin, request, queryset):
    """Admin action to test carryforward system"""
    try:
        call_command('process_carryforward_leaves', action='test', dry_run=True)
        messages.success(request, "Carryforward system test completed successfully!")
    except Exception as e:
        messages.error(request, f"Error testing carryforward system: {e}")

carryforward_test_action.short_description = "Test carryforward system (dry run)"


# Custom admin buttons for the changelist
def carryforward_admin_buttons(obj):
    """Generate admin buttons for carryforward actions"""
    return format_html(
        '<a class="button" href="/admin/carryforward-grant/" style="background-color: #28a745; color: white; margin-right: 5px;">Grant Carryforward</a>'
        '<a class="button" href="/admin/carryforward-cleanup/" style="background-color: #dc3545; color: white; margin-right: 5px;">Cleanup Carryforward</a>'
        '<a class="button" href="/admin/carryforward-test/" style="background-color: #007bff; color: white;">Test System</a>'
    )

carryforward_admin_buttons.short_description = 'Carryforward Actions'
carryforward_admin_buttons.allow_tags = True


# Usage example for Employee admin
class EmployeeAdminWithCarryforward(CarryforwardAdminMixin, admin.ModelAdmin):
    """
    Example of how to add carryforward actions to Employee admin
    """
    list_display = ['user', 'available_leaves', 'carryforward_available_leaves', 'leaves_taken']
    actions = [carryforward_grant_action, carryforward_cleanup_action, carryforward_test_action]
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['carryforward_buttons'] = format_html(
            '<div style="margin-bottom: 10px;">'
            '<a class="button" href="carryforward-grant/" style="background-color: #28a745; color: white; margin-right: 5px;">🎄 Grant Carryforward</a>'
            '<a class="button" href="carryforward-cleanup/" style="background-color: #dc3545; color: white; margin-right: 5px;">🧹 Cleanup Carryforward</a>'
            '<a class="button" href="carryforward-test/" style="background-color: #007bff; color: white;">🧪 Test System</a>'
            '</div>'
        )
        return super().changelist_view(request, extra_context)


"""
USAGE INSTRUCTIONS:

1. Add to your admin.py:

from .admin_actions import CarryforwardAdminMixin, carryforward_grant_action, carryforward_cleanup_action, carryforward_test_action

class EmployeeAdmin(CarryforwardAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'available_leaves', 'carryforward_available_leaves']
    actions = [carryforward_grant_action, carryforward_cleanup_action, carryforward_test_action]

admin.site.register(Employe, EmployeeAdmin)

2. Create admin templates (optional):

templates/admin/carryforward_confirm.html
templates/admin/carryforward_result.html
templates/admin/carryforward_error.html

3. Access via Django admin:
- Go to /admin/
- Select employees or managers
- Use the action dropdown or custom buttons
"""
