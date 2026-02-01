from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Level, Filiere, StudentGroup, Room, Course, 
    ScheduledSession, ReservationRequest, TeacherUnavailability
)

# ============= USER ADMIN =============
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('University Info', {'fields': ('role', 'student_group', 'profile_picture')}),
    )
    list_display = ['username', 'email', 'role', 'student_group', 'is_staff']
    list_filter = ['role', 'student_group__filiere']

admin.site.register(User, CustomUserAdmin)


# ============= HIERARCHY ADMINS =============
@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']


@admin.register(Filiere)
class FiliereAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'level']
    list_filter = ['level']
    search_fields = ['code', 'name']


@admin.register(StudentGroup)
class StudentGroupAdmin(admin.ModelAdmin):
    list_display = ['filiere', 'name', 'capacity']
    list_filter = ['filiere__level', 'filiere']
    search_fields = ['filiere__code', 'name']


# ============= OTHER ADMINS =============
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'capacity', 'equipment', 'building']
    search_fields = ['name']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'session_type', 'filiere', 'group', 'teacher', 'student_count']
    list_filter = ['session_type', 'filiere__level', 'filiere']
    search_fields = ['name', 'code']


@admin.register(ScheduledSession)
class ScheduledSessionAdmin(admin.ModelAdmin):
    list_display = ['course', 'room', 'day', 'start_hour', 'end_hour']
    list_filter = ['day', 'course__filiere']


@admin.register(ReservationRequest)
class ReservationRequestAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'room', 'day', 'start_hour', 'status', 'created_at']
    list_filter = ['status', 'day']
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        queryset.update(status='APPROVED')
    approve_requests.short_description = "Approve selected requests"
    
    def reject_requests(self, request, queryset):
        queryset.update(status='REJECTED')
    reject_requests.short_description = "Reject selected requests"


@admin.register(TeacherUnavailability)
class TeacherUnavailabilityAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'day', 'start_hour', 'end_hour']
    list_filter = ['day', 'teacher']