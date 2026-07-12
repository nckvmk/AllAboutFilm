/* Adds a press-and-hold "reveal" eye icon to every password field: the input
 * shows as plain text only while the icon is held down. jQuery. */

$(function () {
    function hideAll() {
        $('.pw-reveal-wrap input').attr('type', 'password');
    }

    $('input[type="password"]').each(function () {
        var $input = $(this);
        var $wrap = $('<div class="pw-reveal-wrap"></div>');
        $input.before($wrap);
        $wrap.append($input);

        // Keep the crispy error message a sibling of the input (so Bootstrap
        // still shows it) by moving it into the wrap after the input.
        var $feedback = $wrap.next('.invalid-feedback');
        if ($feedback.length) {
            $wrap.append($feedback);
        }

        var $btn = $(
            '<button type="button" class="pw-reveal-btn" aria-label="Show password (hold)">' +
            '<i class="fas fa-eye"></i></button>'
        );
        $input.after($btn);

        $btn.on('mousedown touchstart', function (e) {
            e.preventDefault();
            $input.attr('type', 'text');
        });
    });

    // Release anywhere (or leaving the window) re-hides the password.
    $(document).on('mouseup touchend mouseleave', hideAll);
});
