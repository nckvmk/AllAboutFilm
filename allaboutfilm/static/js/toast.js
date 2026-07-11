/* Dummy "added to cart" toast. Nothing is persisted yet - the real cart is
 * wired up later. Uses jQuery and document.querySelector (no getElementById). */

$(function () {
    function showToast(message) {
        var $toast = $('<div class="cart-toast" role="status" aria-live="polite"></div>')
            .html('<i class="fas fa-check-circle"></i> ' + message);
        $('body').append($toast);
        // Next frame so the CSS transition runs.
        requestAnimationFrame(function () { $toast.addClass('show'); });
        setTimeout(function () {
            $toast.removeClass('show');
            setTimeout(function () { $toast.remove(); }, 300);
        }, 2600);
    }

    $(document).on('click', '.add-to-cart-btn', function (e) {
        e.preventDefault();
        var name = $(this).data('name') || 'Item';
        showToast('<strong>' + name + '</strong> was added to your cart!');
    });
});
