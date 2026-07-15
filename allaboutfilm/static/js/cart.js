/* Shopping cart page: quantity +/- and remove, with a live subtotal.
 * (Shipping/grand total now live on the checkout page.) jQuery.
 * Relies on window.showToast / window.getCsrfToken / window.updateCartBadge
 * defined in toast.js. */

$(function () {
    function money(value) {
        return '€' + Number(value).toFixed(2);
    }

    function setSubtotal(value) {
        $('.summary-subtotal').text(money(value));
    }

    function setCount(count) {
        $('.cart-item-count').text(count + ' item' + (count === 1 ? '' : 's'));
        window.updateCartBadge(count);
    }

    // Ignore clicks on a row that already has a request in flight, so rapid
    // clicking can't fire overlapping requests that race on the session.
    function busy($row) {
        return $row.hasClass('cart-busy');
    }

    // ---- Quantity +/- (film rows) ----
    $('#cart-items').on('click', '.qty-increase, .qty-decrease', function () {
        var $row = $(this).closest('.cart-row');
        if (busy($row)) return;
        $row.addClass('cart-busy');
        var action = $(this).hasClass('qty-increase') ? 'inc' : 'dec';
        $.ajax({
            url: '/cart/update/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: { code: $row.data('code'), action: action },
            dataType: 'json'
        }).done(function (res) {
            $row.find('.qty-value').text(res.quantity);
            $row.find('.cart-line-total').text(money(res.line_total));
            setSubtotal(res.subtotal);
            setCount(res.cart_count);
            if (!res.ok && res.message) {
                window.showToast(res.message, 'error');
            }
        }).always(function () {
            $row.removeClass('cart-busy');
        });
    });

    // ---- Remove ----
    $('#cart-items').on('click', '.cart-remove-btn', function () {
        var $row = $(this).closest('.cart-row');
        if (busy($row)) return;
        $row.addClass('cart-busy');
        $.ajax({
            url: '/cart/remove/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: { code: $row.data('code') },
            dataType: 'json'
        }).done(function (res) {
            $row.remove();
            setSubtotal(res.subtotal);
            setCount(res.cart_count);
            window.showToast(res.message);
            if (res.empty) {
                $('#cart-items').html('<p class="cart-empty text-center py-5">Your shopping cart is empty.</p>');
                $('.summary-subtotal').closest('.cart-summary').find('a.btn')
                    .replaceWith('<button type="button" class="btn btn-dark w-100 py-2" disabled>Proceed to Checkout</button>');
            }
        });
    });
});
