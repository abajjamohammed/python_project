from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Room, Course, ScheduledSession
from .models import ReservationRequest
#added the tabes here just to appear for the admin,so that he can manage them :mohammed 25/01

class CustomUserAdmin(UserAdmin):
    # this line adds a "Personal Info" section at the bottom of the user form
   fieldsets = UserAdmin.fieldsets + (
           ('Informations Personnalisées', {'fields': ('role', 'student_group')}),
       )
   # This line allows viewing the role directly in the user list
   list_display = ['username', 'email', 'role', 'student_group', 'is_staff']
   
#To properly manage the custom user
admin.site.register(User, CustomUserAdmin)

#for the other tables
admin.site.register(Room)
admin.site.register(Course)
admin.site.register(ScheduledSession)
admin.site.register(ReservationRequest)