from django.urls import path

from managers import views

app_name ="managers"

urlpatterns=[

    path("",views.index, name="index"),
    path("founder-dashboard/", views.founder_dashboard, name="founder_dashboard"),
    path("manager-dashboard/", views.manager_dashboard, name="manager_dashboard"),
    path("login/",views.login, name="login"),
    path("founder/login/", views.founder_login, name="founder_login"),
    path("logout/",views.logout, name="logout"),

    path("profile/", views.view_profile, name="view_profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),

    path("manager/leave-details/<int:manager_id>/", views.founder_manager_leave_detail, name="founder_manager_leave_detail"),
    path("manager/full-details/<int:id>/", views.manager_full_details, name="manager_full_details"),
    

    path("leavelist/",views.leave_requests, name="leavelist"),
    path("leave/<int:id>/",views.viewlist, name="viewlist"),
    # FIX: Consistent and non-conflicting URL structure for employee leave actions.
    path('leave/<int:pk>/approve/', views.approve_leave, name='approve_leave'),
    path('leave/<int:pk>/reject/', views.reject_leave, name='reject_leave'),

    # Employee leave actions
    path('employe/leave/approve/<int:leave_id>/', views.approve_employee_leave, name='approve_employee_leave'),
    path('employe/leave/reject/<int:leave_id>/', views.reject_employee_leave, name='reject_employee_leave'),

    path("employee/add/", views.add_employe, name="add_employe"),
    path("employe/edit/<int:id>/", views.edit_employe, name="edit_employe"),
    
    path("employe/details/<int:id>/", views.details, name="details"),

    path('holiday/add/', views.add_holiday, name='add_holiday'),
    path('holiday/delete/<int:id>/', views.delete_holiday, name='delete_holiday'),
    path('bulk-delete-holidays/', views.bulk_delete_holidays, name='bulk_delete_holidays'),  # Add this line

    path('forget-password/', views.manager_forget_password, name='forget_password'),
    path('reset-password/', views.manager_reset_password, name='reset_password'),
    path('resend-otp/', views.manager_resend_otp, name='resend_otp'),

    path("founder/add/", views.founder_add, name="add_founder"),
    path("founder/delete/<int:id>/", views.delete_founder, name="delete_founder"),
    path("manager/add/", views.add_manager, name="add_manager"),
    path("manager/delete/<int:id>/", views.delete_manager, name="delete_manager"),
    path("delete_employee/<int:id>/", views.delete_employee, name="delete_employee"),

    # Holiday Management URLs
    path("holidays/", views.holidays_list, name="holidays_list"),
    path("employees/", views.employees_list, name="employees_list"),

    # Manager Leave Management URLs
    path("leave/apply/", views.manager_apply_leave, name="manager_apply_leave"),
    path("leave/history/", views.manager_leave_history, name="manager_leave_history"),
    path("leave/cancel/<int:id>/", views.manager_cancel_leave, name="manager_cancel_leave"),
    # Manager leave actions
    path("manager/leave/requests/", views.manager_leave_requests_list, name="manager_leave_requests_list"),
    path("manager/leave/view/<int:id>/", views.view_manager_leave_request, name="view_manager_leave_request"),
    path("manager/leave/approve/<int:id>/", views.approve_manager_leave, name="approve_manager_leave"),
    path("manager/leave/reject/<int:id>/", views.reject_manager_leave, name="reject_manager_leave"),

    # All Leave History (for founders)
    path("all-leave-history/", views.all_leave_history, name="all_leave_history"),
    path("leave-summary/", views.leave_summary, name="leave_summary"),

    # New URLs
    path("employee-leave-history/", views.employee_leave_history, name="employee_leave_history"),
    path("employee_detail/<int:id>/", views.employee_detail, name="employee_detail"),

    path('employee/<int:employee_id>/leave-details/', views.manager_employee_leave_detail, name='manager_employee_leave_detail'),

    path('founder/employee/<int:employee_id>/leave-details/', views.founder_employee_leave_detail, name='founder_employee_leave_detail'),
    path('founder-manager-leave-detail/<int:manager_id>/', views.founder_manager_leave_detail, name='founder_manager_leave_detail'),
]
