from django.urls import path
from . import views

urlpatterns = [
    # Admin Dashboard
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Teacher Route
    path('my-timetable/', views.teacher_timetable, name='teacher_timetable'),

    # Student Route
    path('class-timetable/', views.student_timetable, name='student_timetable'),
    path('my-classes/', views.student_classes, name='student_classes'),

    # This connects the 'Generate' button on the dashboard to the view
    path('generate/', views.generate_timetable, name='generate'),
    path('teachers/edit/<int:teacher_id>/', views.edit_teacher, name='edit_teacher'),
    path('teachers/delete/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),
   
]