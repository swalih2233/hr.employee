from django.urls import path
from . import views

app_name = 'leaves'

urlpatterns = [
    path('history/', views.leave_history, name='leave_history'),
    path('requests/', views.leave_requests, name='leave_requests'),
    path('manager-history/', views.manager_leave_history, name='manager_leave_history'),
    path('apply/', views.apply_leave, name='apply_leave'),
    path('update/<int:pk>/<str:status>/', views.update_leave_status, name='update_leave_status'),
]
