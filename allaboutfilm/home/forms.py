"""Forms for the home app, rendered with django-crispy-forms (Bootstrap 5)."""

import re

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit

User = get_user_model()

# Names: letters (plus spaces, hyphens and apostrophes for names like "Anne-Marie"
# or "O'Brien"), but no digits.
name_validator = RegexValidator(
    regex=r"^[A-Za-z\s'-]+$",
    message="Only letters are allowed (no numbers).",
)


def validate_strong_password(value):
    """At least 8 chars with upper- and lower-case letters, a number and a
    special character."""
    missing = []
    if len(value) < 8:
        missing.append("at least 8 characters")
    if not re.search(r"[A-Z]", value):
        missing.append("an uppercase letter")
    if not re.search(r"[a-z]", value):
        missing.append("a lowercase letter")
    if not re.search(r"\d", value):
        missing.append("a number")
    if not re.search(r"[^A-Za-z0-9]", value):
        missing.append("a special character")
    if missing:
        raise ValidationError("Password must contain " + ", ".join(missing) + ".")


class ContactForm(forms.Form):
    first_name = forms.CharField(
        label="First Name",
        min_length=2,
        max_length=50,
        validators=[name_validator],
        widget=forms.TextInput(attrs={"placeholder": "Joe"}),
    )
    last_name = forms.CharField(
        label="Last Name",
        min_length=2,
        max_length=50,
        validators=[name_validator],
        widget=forms.TextInput(attrs={"placeholder": "Mama"}),
    )
    email = forms.EmailField(
        label="Email",
        max_length=50,
        widget=forms.EmailInput(attrs={"placeholder": "joemama@example.com"}),
    )
    subject = forms.CharField(
        label="Subject",
        min_length=2,
        max_length=100,
        widget=forms.TextInput(
            attrs={"placeholder": "Please enter the subject of your message"}
        ),
    )
    message = forms.CharField(
        label="Message",
        min_length=10,
        max_length=300,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "300 characters max"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "contact"
        self.helper.form_method = "post"
        self.helper.form_class = "contact-form py-4"
        # Turn off the browser's built-in validation so Django performs all
        # the checks and crispy renders the resulting error messages.
        self.helper.attrs = {"novalidate": ""}
        self.helper.layout = Layout(
            Row(
                Column("first_name", css_class="col-sm-6 mb-3"),
                Column("last_name", css_class="col-sm-6 mb-3"),
                css_class="row",
            ),
            "email",
            "subject",
            "message",
            Submit("submit", "Submit"),
        )


class LoginForm(forms.Form):
    username_or_email = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={"placeholder": "Username or email"}),
    )
    password = forms.CharField(label="Password", widget=forms.PasswordInput())
    remember_me = forms.BooleanField(label="Remember me", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {"novalidate": ""}
        self.helper.layout = Layout(
            "username_or_email",
            "password",
            "remember_me",
            Submit("submit", "Log In", css_class="w-100"),
        )


class RegistrationForm(forms.Form):
    first_name = forms.CharField(
        label="First Name", min_length=2, max_length=50, validators=[name_validator]
    )
    last_name = forms.CharField(
        label="Last Name", min_length=2, max_length=50, validators=[name_validator]
    )
    email = forms.EmailField(label="Email", max_length=254)
    username = forms.CharField(label="Username", max_length=150)
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(),
        validators=[validate_strong_password],
    )
    confirm_password = forms.CharField(
        label="Confirm Password", widget=forms.PasswordInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {"novalidate": ""}
        self.helper.layout = Layout(
            Row(
                Column("first_name", css_class="col-sm-6"),
                Column("last_name", css_class="col-sm-6"),
            ),
            "email",
            "username",
            "password",
            "confirm_password",
            Submit("submit", "Register", css_class="w-100"),
        )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if password and confirm and password != confirm:
            self.add_error("confirm_password", "Passwords do not match. Please try again.")
        return cleaned


class PasswordRecoveryForm(forms.Form):
    username_or_email = forms.CharField(label="Username or Email")
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(),
        validators=[validate_strong_password],
    )
    confirm_new_password = forms.CharField(
        label="Confirm New Password", widget=forms.PasswordInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = None
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {"novalidate": ""}
        self.helper.layout = Layout(
            "username_or_email",
            "new_password",
            "confirm_new_password",
            Submit("submit", "Reset Password", css_class="w-100"),
        )

    def clean(self):
        cleaned = super().clean()
        identifier = cleaned.get("username_or_email")
        if identifier:
            self._user = (
                User.objects.filter(username__iexact=identifier).first()
                or User.objects.filter(email__iexact=identifier).first()
            )
            if self._user is None:
                self.add_error(
                    "username_or_email",
                    "No account matches that username or email.",
                )
        password = cleaned.get("new_password")
        confirm = cleaned.get("confirm_new_password")
        if password and confirm and password != confirm:
            self.add_error("confirm_new_password", "Passwords do not match. Please try again.")
        return cleaned

    def get_user(self):
        return self._user
