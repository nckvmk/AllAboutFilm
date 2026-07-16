/* Manager inventory panel: swap the table by category, and delete rows with a
 * double confirmation. Add/Edit are placeholders for now. jQuery. Relies on
 * window.showToast / window.getCsrfToken from toast.js. */

$(function () {
    var $container = $('#inventory-table-container');
    if (!$container.length) return;

    // ---- Category dropdown -> reload table ----
    $('#inventory-category').on('change', function () {
        $.get('/manager/inventory/', { category: this.value }).done(function (html) {
            $container.html(html);
        }).fail(function () {
            window.showToast('Could not load that category.', 'error');
        });
    });

    // ---- Delete (double confirmation) ----
    $container.on('click', '.inventory-delete', function () {
        var $btn = $(this);
        var code = $btn.data('code');
        var name = $btn.data('name') || 'this item';

        if (!confirm('Delete "' + name + '" from the inventory?')) return;
        if (!confirm('This cannot be undone. Permanently delete "' + name + '"?')) return;

        $.ajax({
            url: '/manager/inventory/delete/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: { code: code },
            dataType: 'json'
        }).done(function (res) {
            if (res.ok) {
                $btn.closest('tr').remove();
            }
            window.showToast(res.message, res.ok ? 'success' : 'error');
        }).fail(function () {
            window.showToast('Delete failed. Please try again.', 'error');
        });
    });

    // ---- Add / Edit (forms come next) ----
    $container.on('click', '.inventory-add, .inventory-edit', function () {
        window.showToast('The add/edit form is coming soon.');
    });
});
