/* Checkout page behaviour:
 *   1. Show/hide the shipping address fields based on the "same as billing" box.
 *   2. Show/hide the card fields based on the selected payment method.
 *   3. Live-update Delivery + Grand Total from the chosen shipping method.
 * jQuery. Reads window.SHIPPING_PRICES ({pk: price}) rendered by the template. */

$(function () {
    var prices = window.SHIPPING_PRICES || {};

    function money(value) {
        return '€' + Number(value).toFixed(2);
    }

    // ---- Shipping address fields ----
    var $sameBox = $('input[name="shipping_same_as_billing"]');
    function toggleShipping() {
        $('#shipping-fields').toggle(!$sameBox.prop('checked'));
    }
    $sameBox.on('change', toggleShipping);
    toggleShipping();

    // ---- Card fields ----
    function toggleCard() {
        var method = $('input[name="payment_method"]:checked').val();
        $('#card-fields').toggle(method === 'CARD');
    }
    $(document).on('change', 'input[name="payment_method"]', toggleCard);
    toggleCard();

    // ---- Delivery + grand total ----
    var $grand = $('.checkout-grand-total');
    var subtotal = parseFloat($grand.attr('data-subtotal')) || 0;

    $('select[name="shipping_method"]').on('change', function () {
        var price = prices[this.value];
        if (typeof price === 'undefined') {
            $('.checkout-delivery').text('—');
            $grand.text(money(subtotal));
        } else {
            $('.checkout-delivery').text(money(price));
            $grand.text(money(subtotal + price));
        }
    });
});
