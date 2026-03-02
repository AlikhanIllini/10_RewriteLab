"""
Django forms for RewriteLab.

Provides:
- SessionCreateForm: Create a new rewrite session
- UserRegisterForm: User registration with email
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import RewriteSession, RewriteContext, ToneOption


class SessionCreateForm(forms.ModelForm):
    """
    Form for creating a new RewriteSession.

    Users provide their original text, select a writing context and tone,
    and optionally specify audience and purpose.
    """

    class Meta:
        model = RewriteSession
        fields = ['original_text', 'context', 'tone', 'audience', 'purpose']
        widgets = {
            'original_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Paste the text you want rewritten...',
            }),
            'context': forms.Select(attrs={
                'class': 'form-control',
            }),
            'tone': forms.Select(attrs={
                'class': 'form-control',
            }),
            'audience': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., professor, manager, client',
            }),
            'purpose': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., request extension, follow up, apologize',
            }),
        }
        labels = {
            'original_text': 'Your Text',
            'context': 'Writing Context',
            'tone': 'Tone',
            'audience': 'Audience (optional)',
            'purpose': 'Purpose (optional)',
        }
        help_texts = {
            'original_text': 'Minimum 10 characters. Paste the email, message, or text you want improved.',
            'context': 'What kind of writing is this?',
            'tone': 'How should the rewrite sound?',
            'audience': 'Who will read this?',
            'purpose': 'What are you trying to accomplish?',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active contexts and tones
        self.fields['context'].queryset = RewriteContext.objects.filter(is_active=True)
        self.fields['tone'].queryset = ToneOption.objects.filter(is_active=True)


class UserRegisterForm(UserCreationForm):
    """
    Extended user registration form with email field.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password',
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

