from django import forms

# ⚠️ UPDATE THIS LINE: Import both ReservationRequest AND Course
from .models import ReservationRequest, Course, ScheduledSession, User

# --- Your Friend's Code (Leave this alone) ---
class ReservationForm(forms.ModelForm):
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