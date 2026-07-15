"""Forms for the home app, rendered with django-crispy-forms (Bootstrap 5)."""

import datetime
import re

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit

from .models import ShippingMethod

User = get_user_model()

phone_validator = RegexValidator(
    regex=r"^[+\d][\d\s\-().]{6,}$",
    message="Enter a valid phone number.",
)
postal_validator = RegexValidator(
    regex=r"^\d{5}$",
    message="Enter a valid 5-digit postal code.",
)

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
        widget=forms.TextInput(),
    )
    password = forms.CharField(label="Password", widget=forms.PasswordInput())
    remember_me = forms.BooleanField(label="Remember me", required=False)
    next = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {"novalidate": ""}
        self.helper.layout = Layout(
            "username_or_email",
            "password",
            "remember_me",
            "next",
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


class CustomerProfileForm(forms.ModelForm):
    """Customer account-administration panel: edit personal info + avatar."""

    first_name = forms.CharField(
        label="First Name", min_length=2, max_length=50, validators=[name_validator]
    )
    last_name = forms.CharField(
        label="Last Name", min_length=2, max_length=50, validators=[name_validator]
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "nickname", "avatar", "region", "country"]
        labels = {"nickname": "Nickname", "avatar": "Profile Picture"}

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
            "nickname",
            "avatar",
            Row(
                Column("region", css_class="col-sm-6"),
                Column("country", css_class="col-sm-6"),
            ),
            Submit("profile_submit", "Save Changes", css_class="w-100"),
        )


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


class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = [
        ("INSTORE", "Cash/Card in-store"),
        ("CARD", "Card"),
        ("APPLE_PAY", "Apple Pay"),
        ("GOOGLE_PAY", "Google Pay"),
        ("PAYPAL", "PayPal"),
        ("KLARNA", "Klarna"),
        ("PAY_BY_BANK", "Pay By Bank"),
    ]

    # Contact
    first_name = forms.CharField(label="First Name", min_length=2, max_length=50, validators=[name_validator])
    last_name = forms.CharField(label="Last Name", min_length=2, max_length=50, validators=[name_validator])
    email = forms.EmailField(label="E-mail")
    phone = forms.CharField(label="Phone", max_length=30, validators=[phone_validator])

    # Billing address
    billing_address = forms.CharField(label="Address", max_length=255)
    billing_region = forms.CharField(label="Region", max_length=100)
    billing_country = forms.CharField(label="Country", max_length=100)
    billing_postal_code = forms.CharField(label="Postal Code", max_length=5, validators=[postal_validator])

    # Shipping address (required only when different from billing)
    shipping_same_as_billing = forms.BooleanField(
        label="Shipping address is the same as my billing address",
        required=False, initial=True,
    )
    shipping_address = forms.CharField(label="Address", max_length=255, required=False)
    shipping_region = forms.CharField(label="Region", max_length=100, required=False)
    shipping_country = forms.CharField(label="Country", max_length=100, required=False)
    shipping_postal_code = forms.CharField(label="Postal Code", max_length=5, required=False, validators=[postal_validator])

    # Payment
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES, widget=forms.RadioSelect)
    card_number = forms.CharField(label="Card Number", max_length=19, required=False)
    card_exp_month = forms.CharField(label="Month (MM)", max_length=2, required=False)
    card_exp_year = forms.CharField(label="Year (YY)", max_length=2, required=False)
    card_cvc = forms.CharField(label="CVC", max_length=3, required=False)

    # Shipping method + terms
    shipping_method = forms.ModelChoiceField(
        queryset=ShippingMethod.objects.none(),
        empty_label="Nothing selected",
        label="Shipping Method",
    )
    agree_terms = forms.BooleanField(
        label="I Agree to the Terms & Conditions",
        error_messages={"required": "You must agree to the Terms & Conditions to place your order."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shipping_method"].queryset = ShippingMethod.objects.filter(is_active=True)

        text_fields = [
            "first_name", "last_name", "email", "phone",
            "billing_address", "billing_region", "billing_country", "billing_postal_code",
            "shipping_address", "shipping_region", "shipping_country", "shipping_postal_code",
            "card_number", "card_exp_month", "card_exp_year", "card_cvc",
        ]
        for name in text_fields:
            self.fields[name].widget.attrs.update({"class": "form-control"})
        self.fields["shipping_method"].widget.attrs.update({"class": "form-select"})
        self.fields["payment_method"].widget.attrs.update({"class": "form-check-input"})
        self.fields["shipping_same_as_billing"].widget.attrs.update({"class": "form-check-input"})
        self.fields["agree_terms"].widget.attrs.update({"class": "form-check-input"})
        self.fields["card_number"].widget.attrs.update({"placeholder": "1234 5678 9012 3456", "inputmode": "numeric", "maxlength": "19"})
        self.fields["card_exp_month"].widget.attrs.update({"placeholder": "MM", "inputmode": "numeric", "maxlength": "2"})
        self.fields["card_exp_year"].widget.attrs.update({"placeholder": "YY", "inputmode": "numeric", "maxlength": "2"})
        self.fields["card_cvc"].widget.attrs.update({"placeholder": "CVC", "inputmode": "numeric", "maxlength": "3"})
        for name in ("billing_postal_code", "shipping_postal_code"):
            self.fields[name].widget.attrs.update({"inputmode": "numeric", "maxlength": "5", "placeholder": "12345"})

    def clean(self):
        cleaned = super().clean()

        # Shipping address required when different from billing.
        if not cleaned.get("shipping_same_as_billing"):
            for field in ("shipping_address", "shipping_region", "shipping_country", "shipping_postal_code"):
                if not cleaned.get(field):
                    self.add_error(field, "This field is required.")

        # Card fields required + validated when paying by card.
        if cleaned.get("payment_method") == "CARD":
            number = (cleaned.get("card_number") or "").replace(" ", "")
            month = cleaned.get("card_exp_month") or ""
            year = cleaned.get("card_exp_year") or ""
            cvc = cleaned.get("card_cvc") or ""

            if not number:
                self.add_error("card_number", "This field is required.")
            elif not number.isdigit() or len(number) != 16:
                self.add_error("card_number", "Enter a valid 16-digit card number.")

            if not month:
                self.add_error("card_exp_month", "This field is required.")
            elif not (month.isdigit() and len(month) == 2 and 1 <= int(month) <= 12):
                self.add_error("card_exp_month", "Enter a valid month (01-12).")

            if not year:
                self.add_error("card_exp_year", "This field is required.")
            elif not (year.isdigit() and len(year) == 2):
                self.add_error("card_exp_year", "Enter a valid year (YY).")

            if not cvc:
                self.add_error("card_cvc", "This field is required.")
            elif not (cvc.isdigit() and len(cvc) == 3):
                self.add_error("card_cvc", "Enter a valid 3-digit CVC.")

            # Reject already-expired cards.
            if (month.isdigit() and year.isdigit() and len(month) == 2
                    and len(year) == 2 and 1 <= int(month) <= 12):
                today = datetime.date.today()
                exp_year, exp_month = 2000 + int(year), int(month)
                if exp_year < today.year or (exp_year == today.year and exp_month < today.month):
                    self.add_error("card_exp_year", "This card has expired.")

        return cleaned
