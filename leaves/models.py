from django.db import models
from employe.models import Employe
from django.conf import settings

class Leave(models.Model):
    employee = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f'{self.employee} - {self.leave_type}'

class LeaveRequest(models.Model):
    employee = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='leave_requests')
    request_date = models.DateField(auto_now_add=True)
    leave_type = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f'{self.employee} - {self.leave_type}'

class LeaveHistory(models.Model):
    employee = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name='leave_history')
    leave_type = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.employee} - {self.leave_type}'
