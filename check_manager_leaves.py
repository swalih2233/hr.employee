#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('D:\\Mavendoer works\\leave\\hr.employee')

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# Setup Django
django.setup()

from managers.models import UnifiedLeaveRequest, Manager, ManagerLeaveRequest
from users.models import User

print("=== CHECKING MANAGER LEAVE REQUESTS ===")

print("\n1. UnifiedLeaveRequest (Manager requests):")
manager_requests = UnifiedLeaveRequest.objects.filter(requested_by_role='manager')
print(f"Total manager requests: {manager_requests.count()}")
for req in manager_requests:
    print(f"  ID: {req.id}, Subject: {req.subject}, Manager: {req.manager.user.email if req.manager else 'None'}, Approved: {req.is_approved}")

print("\n2. ManagerLeaveRequest (Old model):")
old_manager_requests = ManagerLeaveRequest.objects.all()
print(f"Total old manager requests: {old_manager_requests.count()}")
for req in old_manager_requests:
    print(f"  ID: {req.id}, Subject: {req.subject}, Manager: {req.manager.user.email if req.manager else 'None'}, Approved: {req.is_approved}")

print("\n3. All Managers:")
managers = Manager.objects.all()
print(f"Total managers: {managers.count()}")
for mgr in managers:
    print(f"  Manager: {mgr.user.email}, User ID: {mgr.user.id}")

print("\n4. All UnifiedLeaveRequest:")
all_requests = UnifiedLeaveRequest.objects.all()
print(f"Total unified requests: {all_requests.count()}")
for req in all_requests:
    print(f"  ID: {req.id}, Role: {req.requested_by_role}, Subject: {req.subject}, Approved: {req.is_approved}")
