
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, ProfessionalApplication


class RegistrationForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "placeholder": "Enter your email address"
        })
    )
    privacy_consent = forms.BooleanField(
        required=True,
        label="I have read and accept the privacy notice",
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "privacy_consent",
        ]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = self.cleaned_data["email"]

        if commit:
            user.save()

        return user


class ProfessionalApplicationForm(forms.ModelForm):

    class Meta:
        model = ProfessionalApplication

        fields = [
            "full_name",
            "professional_title",
            "organisation",
            "qualifications",
            "licence_number",
            "years_experience",
            "biography",
            "contact_email",
            "consent_to_directory",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={
                "placeholder": "Enter your full name"
            }),

            "professional_title": forms.TextInput(attrs={
                "placeholder": "e.g. Psychologist or Counsellor"
            }),

            "organisation": forms.TextInput(attrs={
                "placeholder": "Your workplace or organisation"
            }),

            "qualifications": forms.Textarea(attrs={
                "placeholder": "Describe your professional qualifications"
            }),

            "licence_number": forms.TextInput(attrs={
                "placeholder": "Professional registration number, if applicable"
            }),

            "years_experience": forms.NumberInput(attrs={
                "min": 0,
                "placeholder": "Years of professional experience"
            }),

            "biography": forms.Textarea(attrs={
                "placeholder": "Introduce yourself and your professional experience"
            }),

            "contact_email": forms.EmailInput(attrs={
                "placeholder": "Your professional email address"
            }),
        }

    def clean_years_experience(self):
        years = self.cleaned_data["years_experience"]

        if years > 70:
            raise forms.ValidationError(
                "Please enter a valid number of years."
            )

        return years
