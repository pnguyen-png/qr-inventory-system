from django import forms
from django.contrib.auth.forms import AuthenticationForm


class SecureLoginForm(AuthenticationForm):
    """Login form with a honeypot field to catch bots."""

    # Honeypot: invisible to humans, bots auto-fill it
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'tabindex': '-1',
            'autocomplete': 'off',
        }),
    )

    def clean(self):
        # If honeypot is filled, this is a bot — don't even attempt auth
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Invalid username or password.')
        return super().clean()

    @property
    def is_bot(self):
        """Check if the honeypot was triggered (call after is_valid())."""
        return bool(self.data.get('website'))
