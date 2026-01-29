from django import forms
from .models import ReservationRequest

class ReservationForm(forms.ModelForm):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday','Saturday')
    ]
    
    HOUR_CHOICES = [(i, f"{i}h") for i in range(8, 20)]

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