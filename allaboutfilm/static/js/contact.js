/* Contact form success handler.
 *
 * Validation is performed server-side by Django (see home/forms.py). When the
 * form validates successfully the view re-renders the page with a #form-success
 * flag; this jQuery script detects that flag on load and thanks the user. */

$(document).ready(function () {
    if ($("#form-success").length) {
        alert("Thank you for reaching out! We will get back to you the soonest.");
    }
});
