/* Manager inventory panel: swap the table by category, add/edit via a modal
 * form, and delete rows with a double confirmation. jQuery. Relies on
 * window.showToast / window.getCsrfToken from toast.js. */

$(function () {
    var $container = $('#inventory-table-container');
    if (!$container.length) return;

    var modalEl = document.querySelector('#inventory-modal');
    var modal = modalEl ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    var $modalContent = $('#inventory-modal-content');

    function currentCategory() { return $('#inventory-category').val(); }

    function reloadTable() {
        $.get('/manager/inventory/', { category: currentCategory() }).done(function (html) {
            $container.html(html);
        });
    }

    // ---- Category dropdown -> reload table ----
    $('#inventory-category').on('change', reloadTable);

    // ---- Open the add / edit form in the modal ----
    function openForm(params) {
        $.get('/manager/inventory/form/', params).done(function (html) {
            $modalContent.html(html);
            modal.show();
        }).fail(function () {
            window.showToast('Could not open the form.', 'error');
        });
    }

    $container.on('click', '.inventory-add', function () {
        openForm({ category: $(this).data('category') });
    });

    $container.on('click', '.inventory-edit', function () {
        openForm({ category: currentCategory(), code: $(this).data('code') });
    });

    // ---- Submit the modal form (multipart, for photo uploads) ----
    $modalContent.on('submit', '#inventory-form', function (e) {
        e.preventDefault();
        var formData = new FormData(this);
        var $submit = $(this).find('button[type="submit"]').prop('disabled', true);
        $.ajax({
            url: '/manager/inventory/save/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: formData,
            processData: false,
            contentType: false,
            dataType: 'json'
        }).done(function (res) {
            if (res.ok) {
                modal.hide();
                window.showToast(res.message);
                reloadTable();
            } else if (res.html) {
                $modalContent.html(res.html);   // re-render with validation errors
            } else {
                window.showToast(res.message || 'Save failed.', 'error');
                $submit.prop('disabled', false);
            }
        }).fail(function () {
            window.showToast('Save failed. Please try again.', 'error');
            $submit.prop('disabled', false);
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
});
