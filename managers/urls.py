from django.urls import path

from managers import views

app_name ="managers"

urlpatterns=[
    path("",views.index, name="index"),
    path("login/",views.login, name="login"),
    path("logout/",views.logout, name="logout"),

    path("manager/<int:id>/",views.manager_details, name="manager_details"),
    path("manager/add/",views.manager_add, name="manager_add"),
    path("manager/edit/<int:id>/",views.manager_edit, name="manager_edit"),

    path("leavelist/",views.leavelist, name="leavelist"),
    path("leave/<int:id>/",views.viewlist, name="viewlist"),
    path("approve/<int:id>/",views.approve_leave, name="approve_leave"),
    path('leave/reject/<int:id>/', views.reject_leave, name='reject_leave'),

    path("update/yearly/",views.update_yearly, name="update_yearly"),
    path("update/march/",views.update_march, name="update_march"),

    path("employe/add/", views.add_employe, name="add_employe"),
    path("employe/edit/<int:id>/", views.edit_employe, name="edit_employe"),
    
    path("employe/details/<int:id>/", views.details, name="details"),

    path('holiday/add/', views.add_holiday, name='add_holiday'),
    path('holiday/delete/<int:id>/', views.delete_holiday, name='delete_holiday'),
    path('bulk-delete-holidays/', views.bulk_delete_holidays, name='bulk_delete_holidays'),  # Add this line

    path('forget-password/', views.manager_forget_password, name='forget_password'),
    path('reset-password/', views.manager_reset_password, name='reset_password'),

]