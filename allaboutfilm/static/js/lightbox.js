/* Catalog image lightbox: click a card image to view an enlarged version,
 * close with the X, a click on the backdrop, or the Escape key.
 * jQuery. */

$(function () {
    var $overlay = $(
        '<div class="lightbox-overlay" aria-hidden="true">' +
        '<button class="lightbox-close" aria-label="Close enlarged image">&times;</button>' +
        '<img class="lightbox-img" alt="">' +
        '</div>'
    );
    $('body').append($overlay);
    var $img = $overlay.find('.lightbox-img');

    function openLightbox(src, alt) {
        $img.attr('src', src).attr('alt', alt || '');
        $overlay.addClass('show').attr('aria-hidden', 'false');
    }

    function closeLightbox() {
        $overlay.removeClass('show').attr('aria-hidden', 'true');
        $img.attr('src', '');
    }

    // Only the visible carousel slide / single image is clickable.
    $(document).on('click', '.card-img-clickable', function () {
        openLightbox($(this).attr('src'), $(this).attr('alt'));
    });

    $overlay.on('click', function (e) {
        if (e.target === this || $(e.target).hasClass('lightbox-close')) {
            closeLightbox();
        }
    });

    $(document).on('keydown', function (e) {
        if (e.key === 'Escape' && $overlay.hasClass('show')) {
            closeLightbox();
        }
    });
});
