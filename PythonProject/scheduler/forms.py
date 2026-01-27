from django import forms
from .models import ReservationRequest

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