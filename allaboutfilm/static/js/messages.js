/* Surfaces Django messages (e.g. "Registration successful") as bottom-right
 * toasts on any page. Self-contained; reuses the .cart-toast styling. jQuery. */

$(function () {
    var container = document.querySelector('#dj-messages');
    if (!container) return;

    function toast(message, isError) {
        var icon = isError ? 'fa-circle-exclamation' : 'fa-check-circle';
        var $t = $('<div class="cart-toast" role="status" aria-live="polite"></div>')
            .addClass(isError ? 'cart-toast--error' : '')
            .html('<i class="fas ' + icon + '"></i> ' + message);
        $('body').append($t);
        requestAnimationFrame(function () { $t.addClass('show'); });
        setTimeout(function () {
            $t.removeClass('show');
            setTimeout(function () { $t.remove(); }, 300);
        }, 3400);
    }

    container.querySelectorAll('.dj-message').forEach(function (el, i) {
        var isError = (el.getAttribute('data-level') || '').indexOf('error') !== -1;
        // Stagger multiple messages slightly.
        setTimeout(function () { toast(el.textContent.trim(), isError); }, i * 350);
    });
});
