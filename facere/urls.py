"""
URL configuration for facere project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from accounts import views

urlpatterns = [
    path('', views.home, name='home'),
    path('principal/register/', views.principal_register, name='principal_register'),
    path('principal/login/', views.principal_login_view, name='principal_login_view'),
    path('principal/dashboard/', views.principal_dashboard, name='principal_dashboard'),
    path('add-teacher/', views.add_teacher, name='add_teacher'),
    path('principal/delete-teacher/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),
    path('principal/schedule/<int:teacher_id>/', views.schedule_teacher, name='schedule_teacher'),
    path('principal/reports/<int:teacher_id>/', views.view_teacher_reports, name='view_teacher_reports'),
    path('principal/analysis/', views.principal_analysis, name='principal_analysis'),
    path('principal/export-defaulters/', views.export_defaulter_csv, name='export_defaulter_csv'),
    path('principal/delete-schedule/<int:timetable_id>/', views.delete_schedule, name='delete_schedule'),
    path('principal/delete-all-schedule/<int:teacher_id>/', views.delete_all_schedule, name='delete_all_schedule'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/profile/', views.teacher_profile, name='teacher_profile'),
    path('teacher/mark-attendance/', views.mark_attendance, name='mark_attendance'),
    path('teacher/login-password/', views.teacher_login_password, name='teacher_login_password'),
    path('login/', views.login_user, name='login_user'),
    path('teacher/start-class/<int:timetable_id>/', views.start_class, name='start_class'),
    path('teacher/live-monitoring/', views.live_class_monitoring, name='live_class_monitoring'),
    path('teacher/update-live-attendance/', views.update_live_attendance, name='update_live_attendance'),
    path('teacher/end-class/', views.end_class, name='end_class'),
    path('teacher/records/', views.previous_records_teacher, name='previous_records_teacher'),
    path('teacher/help/', views.teacher_help, name='teacher_help'),
    path('admin/', admin.site.urls),
]
