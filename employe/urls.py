from django.urls import path

from employe import views

app_name ="employe"

urlpatterns=[
    path("",views.login, name="login"),
    path("dashboard/", views.employee_dashboard, name="employee_dashboard"),
    path("details/",views.details, name="details"),
    path("leaveform/",views.leaveform, name="leaveform"),
    path("apply-leave/", views.apply_leave, name="apply_leave"),  # Fixed: Added required URL pattern

    path("logout/",views.logout, name="logout"),

    path("leavelist/",views.leavelist, name="leavelist"),
    path("leavelist/cancel/<int:id>/", views.cancel_leave, name="cancel_leave"),
    path("leavelist/withdraw/<int:id>/", views.withdraw_leave, name="withdraw_leave"),
    path("leave/<int:id>/",views.viewlist, name="viewlist"),

    path("employe/edit/<int:id>/", views.edit_employe, name="edit_employe"),
    path("add-employe/", views.add_employe, name="add_employe"),
    path("subordinate-leaves/", views.subordinate_leave_requests, name="subordinate_leave_requests"),
    path("subordinate-leaves/approve/<int:leave_id>/", views.approve_subordinate_leave, name="approve_subordinate_leave"),
    path("subordinate-leaves/reject/<int:leave_id>/", views.reject_subordinate_leave, name="reject_subordinate_leave"),
    path("subordinate-leaves/withdraw/approve/<int:leave_id>/", views.approve_subordinate_withdrawal, name="approve_subordinate_withdrawal"),
    path("subordinate-leaves/withdraw/reject/<int:leave_id>/", views.reject_subordinate_withdrawal, name="reject_subordinate_withdrawal"),

    path('forget-password/',views.forget_password, name='forget_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
]
