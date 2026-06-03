from django.db import models
from employe.models import Employe
from django.conf import settings

class Leave(models.Model):
    employee = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, default='Pending')

    def __str__(self):
        return f'{self.employee} - {self.leave_type}'

class LeaveRequest(models.Model):
    LEAVE_CHOICES = (
        ('ML', 'Medical Leave'),
        ('AL', 'Annual Leave'),
    )

    ROLE_CHOICES = (
        ('employee', 'Employee'),
        ('manager', 'Manager'),
    )
    
    employee = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='leave_requests', null=True, blank=True)
    manager = models.ForeignKey('managers.Manager', on_delete=models.CASCADE, null=True, blank=True, related_name='leave_requests')
    request_date = models.DateField(auto_now_add=True)
    leave_type = models.CharField(max_length=100, choices=LEAVE_CHOICES, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, default='Pending')
    requested_by_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_leaves')
    leave_duration = models.IntegerField(default=0)
    subject = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    file = models.FileField(null=True, blank=True, upload_to='leave_files')

    def __str__(self):
        if self.requested_by_role == 'manager' and self.manager:
            return f"Manager: {self.manager.user.email} - {self.subject}"
        elif self.requested_by_role == 'employee' and self.employee:
            return f"Employee: {self.employee.user.email} - {self.subject}"
        return f"Leave Request: {self.subject}"

class LeaveHistory(models.Model):
    employee = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='leave_history')
    leave_type = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.employee} - {self.leave_type}'
