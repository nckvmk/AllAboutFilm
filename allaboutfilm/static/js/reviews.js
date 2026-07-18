/* Reviews: the customer "Leave Feedback" modal on the account page, and the
 * staff feedback-moderation panel (flag / hide / delete). jQuery. Relies on
 * window.showToast / window.getCsrfToken from toast.js. */

$(function () {
    // =====================================================================
    // Customer: leave feedback for an order
    // =====================================================================
    var feedbackModalEl = document.querySelector('#feedback-modal');
    if (feedbackModalEl) {
        var feedbackModal = bootstrap.Modal.getOrCreateInstance(feedbackModalEl);
        var $feedbackContent = $('#feedback-modal-content');
        var currentOrderId = null;

        // ---- Open the modal for an order ----
        $('.order-list').on('click', '.feedback-open', function () {
            currentOrderId = $(this).data('order-id');
            $.get('/review/form/', { order_id: currentOrderId }).done(function (html) {
                $feedbackContent.html(html);
                feedbackModal.show();
            }).fail(function () {
                window.showToast('Could not open the feedback form.', 'error');
            });
        });

        // ---- Live character counter on each review textarea ----
        $feedbackContent.on('input', '.review-textarea', function () {
            $(this).closest('.review-item').find('.review-charcount')
                .text(this.value.length + ' / 500');
        });

        // ---- Submit ----
        $feedbackContent.on('submit', '#review-form', function (e) {
            e.preventDefault();
            var $form = $(this);
            var $submit = $form.find('button[type="submit"]').prop('disabled', true);
            $form.find('.review-error').text('');   // clear previous field errors
            $.ajax({
                url: '/review/submit/',
                method: 'POST',
                headers: { 'X-CSRFToken': window.getCsrfToken() },
                data: $form.serialize(),
                dataType: 'json'
            }).done(function (res) {
                if (res.ok) {
                    feedbackModal.hide();
                    window.showToast(res.message);
                    if (res.all_reviewed) {
                        markOrderReviewed(currentOrderId);
                    }
                } else if (res.errors) {
                    $.each(res.errors, function (code, message) {
                        $form.find('.review-error[data-error-for="' + code + '"]').text(message);
                    });
                    $submit.prop('disabled', false);
                } else {
                    window.showToast(res.message || 'Could not submit your feedback.', 'error');
                    $submit.prop('disabled', false);
                }
            }).fail(function () {
                window.showToast('Could not submit your feedback. Please try again.', 'error');
                $submit.prop('disabled', false);
            });
        });

        function markOrderReviewed(orderId) {
            var $cell = $('.feedback-open[data-order-id="' + orderId + '"]').closest('.order-feedback');
            $cell.html('<span class="feedback-done small"><i class="fas fa-check-circle" aria-hidden="true"></i> Reviewed and Rated</span>');
        }
    }

    // =====================================================================
    // Staff: moderate feedback (flag / hide / delete)
    // =====================================================================
    var $feedbackTable = $('#feedback-table-container');
    if ($feedbackTable.length) {
        function reloadFeedback() {
            $.get('/manager/feedback/').done(function (html) {
                $feedbackTable.html(html);
            });
        }

        // ---- Employee: flag for the manager ----
        $feedbackTable.on('click', '.feedback-flag', function () {
            var $btn = $(this).prop('disabled', true);
            $.ajax({
                url: '/manager/feedback/flag/',
                method: 'POST',
                headers: { 'X-CSRFToken': window.getCsrfToken() },
                data: { feedback_id: $btn.data('feedback-id') },
                dataType: 'json'
            }).done(function (res) {
                window.showToast(res.message, res.ok ? 'success' : 'error');
                if (res.ok) { reloadFeedback(); }
                else { $btn.prop('disabled', false); }
            }).fail(function () {
                window.showToast('Could not flag the review.', 'error');
                $btn.prop('disabled', false);
            });
        });

        // ---- Hide / unhide (employee or manager) ----
        $feedbackTable.on('click', '.feedback-hide', function () {
            var $btn = $(this).prop('disabled', true);
            $.ajax({
                url: '/manager/feedback/hide/',
                method: 'POST',
                headers: { 'X-CSRFToken': window.getCsrfToken() },
                data: { feedback_id: $btn.data('feedback-id') },
                dataType: 'json'
            }).done(function (res) {
                window.showToast(res.message, res.ok ? 'success' : 'error');
                if (res.ok) { reloadFeedback(); }
                else { $btn.prop('disabled', false); }
            }).fail(function () {
                window.showToast('Could not update the review.', 'error');
                $btn.prop('disabled', false);
            });
        });

        // ---- Manager: delete outright (destructive -> confirm) ----
        $feedbackTable.on('click', '.feedback-delete', function () {
            var $btn = $(this);
            if (!confirm('Delete this review permanently? This cannot be undone.')) return;
            $.ajax({
                url: '/manager/feedback/delete/',
                method: 'POST',
                headers: { 'X-CSRFToken': window.getCsrfToken() },
                data: { feedback_id: $btn.data('feedback-id') },
                dataType: 'json'
            }).done(function (res) {
                if (res.ok) { $btn.closest('tr').remove(); }
                window.showToast(res.message, res.ok ? 'success' : 'error');
            }).fail(function () {
                window.showToast('Could not delete the review.', 'error');
            });
        });
    }
});
