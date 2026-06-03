import json

from django.http import HttpResponse
from django.shortcuts import reverse
from django.http.response import HttpResponseRedirect


def allow_manager(fuction):
    def wrapper(request, *args, **kwargs):
        current_user = request.user
        if not current_user.is_manager:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                response_data = {
                    "status": "error",
                    "title": "Unauthorized Access",
                    "message": "You can't perform this action"
                }
                return HttpResponse(json.dumps(response_data),content_type="application/json")

            else:
                return HttpResponseRedirect(reverse("managers:logout"))

        
        return fuction(request, *args, **kwargs)

    return wrapper


def allow_employee(fuction):
    def wrapper(request, *args, **kwargs):
        current_user = request.user
        if not current_user.is_employee:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                response_data = {
                    "status": "error",
                    "title": "Unauthorized Access",
                    "message": "You can't perform this action"
                }
                return HttpResponse(json.dumps(response_data),content_type="application/json")

            else:
                return HttpResponseRedirect(reverse("employe:logout"))


        return fuction(request, *args, **kwargs)

    return wrapper


def allow_founder(function):
    """Decorator to allow only founders"""
    def wrapper(request, *args, **kwargs):
        current_user = request.user

        # Check if user is a founder (has Founder profile)
        try:
            from managers.models import Founder
            founder = Founder.objects.get(user=current_user)
        except Founder.DoesNotExist:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                response_data = {
                    "status": "error",
                    "title": "Unauthorized Access",
                    "message": "Only founders can perform this action"
                }
                return HttpResponse(json.dumps(response_data), content_type="application/json")
            else:
                return HttpResponseRedirect(reverse("managers:index"))

        return function(request, *args, **kwargs)
    return wrapper


def allow_manager_or_founder(function):
    """Decorator to allow managers and founders"""
    def wrapper(request, *args, **kwargs):
        current_user = request.user
        if not current_user.is_manager:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                response_data = {
                    "status": "error",
                    "title": "Unauthorized Access",
                    "message": "You can't perform this action"
                }
                return HttpResponse(json.dumps(response_data), content_type="application/json")
            else:
                return HttpResponseRedirect(reverse("managers:logout"))

        return function(request, *args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    """
    Decorator that checks if user has one of the allowed roles
    Usage: @role_required('founder', 'manager')
    """
    def decorator(function):
        def wrapper(request, *args, **kwargs):
            current_user = request.user
            user_roles = []

            # Check user roles
            if current_user.is_employee:
                user_roles.append('employee')
            if current_user.is_manager:
                user_roles.append('manager')

            # Check if user is founder
            try:
                from managers.models import Founder
                Founder.objects.get(user=current_user)
                user_roles.append('founder')
            except Founder.DoesNotExist:
                pass

            # Check if user has any of the allowed roles
            if not any(role in user_roles for role in allowed_roles):
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    response_data = {
                        "status": "error",
                        "title": "Unauthorized Access",
                        "message": f"Access restricted to: {', '.join(allowed_roles)}"
                    }
                    return HttpResponse(json.dumps(response_data), content_type="application/json")
                else:
                    # Redirect based on user type
                    if current_user.is_employee:
                        return HttpResponseRedirect(reverse("employe:details"))
                    elif current_user.is_manager:
                        return HttpResponseRedirect(reverse("managers:index"))
                    else:
                        return HttpResponseRedirect(reverse("managers:login"))

            return function(request, *args, **kwargs)
        return wrapper
    return decorator