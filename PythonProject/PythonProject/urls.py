"""
URL configuration for PythonProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.contrib.auth import views as auth_views # Import Django Auth Views
from scheduler import views


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Dashboard (Home)
    path('', views.admin_dashboard, name='dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),

    # Login Page (Using our custom template)
    path('login/', auth_views.LoginView.as_view(template_name='scheduler/login.html'), name='login'),
    
    # Logout (Redirects to login page),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # --- mohammmed's additions 
    path('reservation/new/', views.make_reservation, name='make_reservation'),
    path('reservations/list/', views.approve_reservations, name='approve_reservations'),
    path('reservations/process/<int:req_id>/<str:action>/', views.process_request, name='process_request'),
    path('generate-schedule/', views.run_timetable_generation, name='generate_schedule'),
]
