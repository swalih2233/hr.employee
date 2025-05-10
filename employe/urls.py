from django.urls import path

from employe import views

app_name ="employe"

urlpatterns=[
    path("",views.details, name="details"),
    path("login/",views.login, name="login"),
    path("leaveform/",views.leaveform, name="leaveform"),

    path("logout/",views.logout, name="logout"),

    path("leavelist/",views.leavelist, name="leavelist"),
    path("leave/<int:id>/",views.viewlist, name="viewlist"),

    path("employe/edit/<int:id>/", views.edit_employe, name="edit_employe"),

    path('forget-password/',views.forget_password, name='forget_password'),
    path('reset-password/', views.reset_password, name='reset_password'),




    

]