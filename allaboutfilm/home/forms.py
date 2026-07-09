"""Forms for the home app, rendered with django-crispy-forms (Bootstrap 5)."""

from django import forms
from django.core.validators import RegexValidator

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit

# Names: letters (plus spaces, hyphens and apostrophes for names like "Anne-Marie"
# or "O'Brien"), but no digits.
name_validator = RegexValidator(
    regex=r"^[A-Za-z\s'-]+$",
    message="Only letters are allowed (no numbers).",
)


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
