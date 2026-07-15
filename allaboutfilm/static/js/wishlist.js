/* Wishlist: heart toggle on product cards / item page, and remove buttons on
 * the account page. jQuery. Relies on window.showToast / window.getCsrfToken
 * from toast.js. */

$(function () {
    // ---- Toggle (heart buttons) ----
    $(document).on('click', '.wishlist-toggle', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var $btn = $(this);
        if ($btn.hasClass('wishlist-busy')) return;
        $btn.addClass('wishlist-busy');

        $.ajax({
            url: '/wishlist/toggle/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: { code: $btn.data('code') },
            dataType: 'json'
        }).done(function (res) {
            if (!res.ok) {
                window.showToast(res.message, 'error');
                return;
            }
            $btn.toggleClass('active', res.in_wishlist);
            $btn.find('i').toggleClass('fas', res.in_wishlist).toggleClass('far', !res.in_wishlist);
            $btn.find('.wishlist-label').text(res.in_wishlist ? 'In Wishlist' : 'Add to Wishlist');
            window.showToast(res.message);
        }).always(function () {
            $btn.removeClass('wishlist-busy');
        });
    });

    // ---- Remove (account page) ----
    $('#wishlist-items').on('click', '.wishlist-remove', function () {
        var $row = $(this).closest('.wishlist-row');
        $.ajax({
            url: '/wishlist/remove/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: { code: $row.data('code') },
            dataType: 'json'
        }).done(function (res) {
            $row.remove();
            window.showToast(res.message);
            if (res.empty) {
                $('#wishlist-items').html('<p class="wishlist-empty text-muted mb-0">Your wishlist is empty.</p>');
            }
        });
    });
});
