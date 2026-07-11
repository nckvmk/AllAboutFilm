/* Shared toast + CSRF helpers, plus the AJAX "add to cart".
 * Uses jQuery and document.querySelector (no getElementById). */

(function () {
    window.getCsrfToken = function () {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    };

    window.showToast = function (message, type) {
        var isError = type === 'error';
        var icon = isError ? 'fa-circle-exclamation' : 'fa-check-circle';
        var $toast = $('<div class="cart-toast" role="status" aria-live="polite"></div>')
            .addClass(isError ? 'cart-toast--error' : '')
            .html('<i class="fas ' + icon + '"></i> ' + message);
        $('body').append($toast);
        requestAnimationFrame(function () { $toast.addClass('show'); });
        setTimeout(function () {
            $toast.removeClass('show');
            setTimeout(function () { $toast.remove(); }, 300);
        }, 2800);
    };

    window.updateCartBadge = function (count) {
        var badge = document.querySelector('.cart-count');
        if (!badge) return;
        badge.textContent = count;
        badge.classList.toggle('d-none', !count);
    };
})();

$(function () {
    $(document).on('click', '.add-to-cart-btn', function (e) {
        e.preventDefault();
        var $btn = $(this);
        var qtyInput = document.querySelector('.qty-input');   // present on film item page
        var quantity = qtyInput ? (parseInt(qtyInput.value, 10) || 1) : 1;

        $.ajax({
            url: '/cart/add/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: { code: $btn.data('code'), quantity: quantity },
            dataType: 'json'
        }).done(function (res) {
            window.showToast(res.message, res.ok ? 'success' : 'error');
            window.updateCartBadge(res.cart_count);
        }).fail(function () {
            window.showToast('Something went wrong. Please try again.', 'error');
        });
    });
});
