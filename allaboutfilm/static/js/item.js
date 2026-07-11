/* Item detail page behaviour:
 *   1. Zoom-on-hover magnifier that enlarges only the area under the cursor.
 *   2. Film quantity selector clamped to available stock.
 * jQuery + document.querySelector only (no getElementById). */

$(function () {
    var ZOOM = 2.5;

    function attachMagnifier(container) {
        var $container = $(container);
        var $img = $container.find('img').first();
        if (!$img.length) return;

        var $lens = $('<div class="zoom-lens" aria-hidden="true"></div>');
        $container.append($lens);

        function refreshBackground() {
            $lens.css({
                'background-image': 'url("' + $img.attr('src') + '")',
                'background-size': ($img.width() * ZOOM) + 'px ' + ($img.height() * ZOOM) + 'px'
            });
        }

        $container.on('mouseenter', function () {
            refreshBackground();
            $lens.show();
        });

        $container.on('mouseleave', function () {
            $lens.hide();
        });

        $container.on('mousemove', function (e) {
            var rect = $img[0].getBoundingClientRect();
            var x = e.clientX - rect.left;
            var y = e.clientY - rect.top;

            if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
                $lens.hide();
                return;
            }
            // Ensure the magnified image is set (covers the case where
            // mouseenter didn't run, e.g. right after a carousel slide).
            refreshBackground();
            $lens.show();

            var lensW = $lens.outerWidth();
            var lensH = $lens.outerHeight();

            // Keep the lens inside the image bounds.
            var lensX = Math.max(0, Math.min(x - lensW / 2, rect.width - lensW));
            var lensY = Math.max(0, Math.min(y - lensH / 2, rect.height - lensH));
            $lens.css({ left: lensX + 'px', top: lensY + 'px' });

            // Show the magnified region centred on the cursor.
            $lens.css('background-position',
                '-' + (x * ZOOM - lensW / 2) + 'px -' + (y * ZOOM - lensH / 2) + 'px');
        });
    }

    document.querySelectorAll('.zoom-container').forEach(attachMagnifier);

    // ---- Film quantity clamp ----
    var qty = document.querySelector('.qty-input');
    if (qty) {
        $(qty).on('input change blur', function () {
            var max = parseInt(this.max, 10);
            var min = parseInt(this.min, 10) || 1;
            var value = parseInt(this.value, 10);
            if (isNaN(value)) { this.value = min; return; }
            if (value > max) this.value = max;
            if (value < min) this.value = min;
        });
    }
});
