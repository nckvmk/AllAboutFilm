/* Shopping cart page: quantity +/-, remove, live subtotal / grand total,
 * and the (dummy for now) checkout guard. jQuery + document.querySelector.
 * Relies on window.showToast / window.getCsrfToken / window.updateCartBadge
 * defined in toast.js. */

$(function () {
    var $summary = $('.cart-summary');

    function money(value) {
        return '€' + Number(value).toFixed(2);
    }

    function subtotal() {
        return parseFloat($summary.attr('data-subtotal')) || 0;
    }

    function shippingPrice() {
        var select = document.querySelector('#shipping-select');
        var opt = select ? select.selectedOptions[0] : null;
        var price = opt ? parseFloat(opt.getAttribute('data-price')) : NaN;
        return isNaN(price) ? null : price;
    }

    function updateGrandTotal() {
        var ship = shippingPrice();
        $('.summary-grand-total').text(money(subtotal() + (ship || 0)));
    }

    function setSubtotal(value) {
        $summary.attr('data-subtotal', value);
        $('.summary-subtotal').text(money(value));
        updateGrandTotal();
    }

    function setCount(count) {
        $('.cart-item-count').text(count + ' item' + (count === 1 ? '' : 's'));
        window.updateCartBadge(count);
    }

    // ---- Shipping selection -> grand total ----
    $('#shipping-select').on('change', updateGrandTotal);

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
            }
        });
    });

    // ---- Checkout guard (dummy until auth exists) ----
    $('#checkout-btn').on('click', function () {
        if (shippingPrice() === null) {
            alert('Please select a shipping method before proceeding to checkout.');
            return;
        }
        alert('You must be logged in to place an order.');
    });
});
