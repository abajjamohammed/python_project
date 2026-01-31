from django import forms
from .models import TeacherUnavailability
from .models import ReservationRequest, Course, ScheduledSession,  User, Course, Room

# --- Your Friend's Code (Leave this alone) ---
class ReservationForm(forms.ModelForm):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday','Saturday')
    ]
    
    HOUR_CHOICES = [(i, f"{i}h") for i in range(9, 20)]

    day = forms.ChoiceField(choices=DAY_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    start_hour = forms.ChoiceField(choices=HOUR_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    end_hour = forms.ChoiceField(choices=HOUR_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    class Meta:
        model = ReservationRequest
        fields = ['room', 'day', 'start_hour', 'end_hour', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'day': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Lundi'}),
            'start_hour': forms.NumberInput(attrs={'class': 'form-control'}),
            'end_hour': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# --- YOUR NEW CODE (Added to the bottom) ---
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'teacher', 'group_name', 'student_count', 'equipment_needed']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Course Name'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'group_name': forms.TextInput(attrs={'class': 'form-control'}),
            'student_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'equipment_needed': forms.TextInput(attrs={'class': 'form-control'}),
        }
        from .models import User # Make sure User is imported

class TeacherForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        # We need custom save logic to Hash the password (security)
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = 'T'  # Force the role to be Teacher
        if commit:
            user.save()
        return user
    

class RoomSearchForm(forms.Form):
    day = forms.ChoiceField(choices=[('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ...]) # Add all days
    start_hour = forms.IntegerField(min_value=8, max_value=18)
    end_hour = forms.IntegerField(min_value=9, max_value=19)
    # Make sure ScheduledSession is imported at the top of the file!
from .models import ScheduledSession 

class SessionForm(forms.ModelForm):
    class Meta:
        model = ScheduledSession
        fields = ['course', 'room', 'day', 'start_hour', 'end_hour']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'day': forms.Select(choices=[
                ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), 
                ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'), 
                ('Friday', 'Friday')
            ], attrs={'class': 'form-select'}),
            'start_hour': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '8'}),
            'end_hour': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '10'}),
        }
class TeacherEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email'] # No password field here
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }



class TeacherUnavailabilityForm(forms.ModelForm):
    class Meta:
        model = TeacherUnavailability
        fields = ['day', 'start_hour', 'end_hour']
        widgets = {
            'day': forms.Select(choices=[
                ('Lundi', 'Monday'),
                ('Mardi', 'Tuesday'),
                ('Mercredi', 'Wednesday'),
                ('Jeudi', 'Thursday'),
                ('Vendredi', 'Friday'),
            ], attrs={'class': 'form-select'}),
            'start_hour': forms.Select(choices=[(h, f'{h}:00') for h in range(8, 19)], attrs={'class': 'form-select'}),
            'end_hour': forms.Select(choices=[(h, f'{h}:00') for h in range(8, 19)], attrs={'class': 'form-select'}),
        }
        labels = {
            'day': 'Day',
            'start_hour': 'Start Time',
            'end_hour': 'End Time',
        }