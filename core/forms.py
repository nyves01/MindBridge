from datetime import date, datetime

from django import forms

from accounts.models import ProfessionalApplication
from .models import Appointment, Feedback


MOOD_CHOICES = (
    ("0", "Mostly positive"),
    ("1", "A mixture of positive and difficult feelings"),
    ("2", "Mostly difficult"),
)

ENERGY_CHOICES = (
    ("0", "Generally have enough energy"),
    ("1", "My energy levels have been changing"),
    ("2", "I have often felt low on energy"),
)

STRESS_CHOICES = (
    ("0", "Generally managed it well"),
    ("1", "Sometimes it feels overwhelming"),
    ("2", "I have found it difficult to manage"),
)

CONNECTION_CHOICES = (
    ("0", "Connected and supported"),
    ("1", "Sometimes connected, sometimes alone"),
    ("2", "Often alone or disconnected"),
)


class SelfAwarenessForm(forms.Form):
    mood = forms.TypedChoiceField(
        choices=MOOD_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
    )
    energy = forms.TypedChoiceField(
        choices=ENERGY_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
    )
    stress = forms.TypedChoiceField(
        choices=STRESS_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
    )
    connection = forms.TypedChoiceField(
        choices=CONNECTION_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
    )


class AppointmentRequestForm(forms.ModelForm):
    requested_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    requested_time = forms.TimeField(
        widget=forms.TimeInput(attrs={"type": "time"}),
    )

    class Meta:
        model = Appointment
        fields = ["requested_date", "requested_time"]

    def clean_requested_date(self):
        requested_date = self.cleaned_data["requested_date"]
        if requested_date < date.today():
            raise forms.ValidationError("Please choose today or a future date.")
        return requested_date

    def clean_requested_time(self):
        return self.cleaned_data["requested_time"]


class RescheduleForm(forms.Form):
    proposed_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    proposed_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))

    def clean_proposed_date(self):
        proposed_date = self.cleaned_data["proposed_date"]
        if proposed_date < date.today():
            raise forms.ValidationError("The proposed date cannot be in the past.")
        return proposed_date


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["category"]
