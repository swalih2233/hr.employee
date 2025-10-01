from django.contrib import admin
from .models import Manager, Founder
from .forms import ManagerAdminForm, FounderAdminForm
from users.models import User

class ManagerAdmin(admin.ModelAdmin):
    form = ManagerAdminForm
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

class FounderAdmin(admin.ModelAdmin):
    form = FounderAdminForm
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