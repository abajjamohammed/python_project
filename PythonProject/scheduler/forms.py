from django import forms
from .models import ReservationRequest

class ReservationForm(forms.ModelForm):
    DAY_CHOICES = [
        ('Lundi', 'Lundi'),
        ('Mardi', 'Mardi'),
        ('Mercredi', 'Mercredi'),
        ('Jeudi', 'Jeudi'),
        ('Vendredi', 'Vendredi'),
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