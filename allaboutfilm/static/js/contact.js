/* This script handles the input validation behavior of the contact form.*/

$(document).ready(function() {
    // Custom validation method for names (letters, spaces, 2-15 chars)

    // Helper: Show error under a field
    function showError(fieldId, message) {
        let $field = $(fieldId);
        // Remove any existing error for this field
        $(fieldId + "_error").remove();
        $field.css("border", "1px solid red");
        // Insert error message after the field (or inside parent .form-group)
        let $errorSpan = $("<span>")
            .attr("id", fieldId.substring(1) + "_error")
            .addClass("error-message")
            .css({
                "color": "red",
                "font-size": "12px",
                "display": "block",
                "margin-top": "4px"
            })
            .text(message);
        $field.after($errorSpan);
    }

    function clearErrors() {
        $(".error-message").remove();
        $(".form-control, input, textarea").css("border", "");
    }

    // Validation logic
    function validateForm() {
        let isValid = true;

        // 1. First Name
        let firstName = $("#firstName").val().trim();
        if (firstName === "") {
            showError("#firstName", "First name is required.");
            isValid = false;
        } else if (!/^[A-Za-z\s]+$/.test(firstName)) {
            showError("#firstName", "First name must contain only letters and spaces.");
            isValid = false;
        } else if (firstName.length < 2 || firstName.length > 15) {
            showError("#firstName", "First name must be between 2 and 15 characters.");
            isValid = false;
        }

        // 2. Last Name
        let lastName = $("#lastName").val().trim();
        if (lastName === "") {
            showError("#lastName", "Last name is required.");
            isValid = false;
        } else if (!/^[A-Za-z\s]+$/.test(lastName)) {
            showError("#lastName", "Last name must contain only letters and spaces.");
            isValid = false;
        } else if (lastName.length < 2 || lastName.length > 15) {
            showError("#lastName", "Last name must be between 2 and 15 characters.");
            isValid = false;
        }

        // 3. Email (required, <=50 chars, valid format with @ and domain)
        let email = $("#email").val().trim();
        let emailPattern = /^[^\s@]+@([^\s@]+\.)+[^\s@]+$/; // basic valid email
        if (email === "") {
            showError("#email", "Email is required.");
            isValid = false;
        } else if (email.length > 50) {
            showError("#email", "Email must not exceed 50 characters.");
            isValid = false;
        } else if (!emailPattern.test(email)) {
            showError("#email", "Please enter a valid email address (e.g., name@domain.com).");
            isValid = false;
        }

        // 4. Subject (required, <=50 chars)
        let subject = $("#subject").val().trim();
        if (subject === "") {
            showError("#subject", "Subject is required.");
            isValid = false;
        } else if (subject.length > 50) {
            showError("#subject", "Subject must not exceed 50 characters.");
            isValid = false;
        }

        // 5. Message (required, 10-300 chars)
        let message = $("#message").val().trim();
        if (message === "") {
            showError("#message", "Message is required.");
            isValid = false;
        } else if (message.length < 4) {
            showError("#message", "Message must be at least 10 characters.");
            isValid = false;
        } else if (message.length > 300) {
            showError("#message", "Message must not exceed 300 characters.");
            isValid = false;
        }

        return isValid;
    }

    // On form submit
    $("#contact").on("submit", function(e) {
        e.preventDefault();  // stop actual form submission
        clearErrors();       // remove previous errors and red borders

        if (validateForm()) {
            // Success
            alert("The form has been submitted successfully. Thank you for reaching out ;)");
            // Optionally reset the form
            this.reset();
            // Remove any remaining error styles
            $(".form-control, input, textarea").css("border", "");
        }
    });

    // Optional: clear error on focus (better UX)
    $(".form-control").on("focus", function() {
        $(this).css("border", "");
        let errorId = $(this).attr("id") + "_error";
        $("#" + errorId).remove();
    });
});
