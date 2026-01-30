from django.urls import path
from . import views

urlpatterns = [
    # Admin Dashboard
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Teacher Route
    path('my-timetable/', views.teacher_timetable, name='teacher_timetable'),

    # Student Route
    path('class-timetable/', views.student_timetable, name='student_timetable'),

    # This connects the 'Generate' button on the dashboard to the view
    path('generate/', views.generate_timetable, name='generate'),
]