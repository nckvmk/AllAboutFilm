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

    // =====================================================================
    // User management
    // =====================================================================
    var $userContainer = $('#user-table-container');

    $('#user-category').on('change', function () {
        $.get('/manager/users/', { category: this.value }).done(function (html) {
            $userContainer.html(html);
        }).fail(function () {
            window.showToast('Could not load that category.', 'error');
        });
    });

    $userContainer.on('click', '.user-suspend-btn', function () {
        var $btn = $(this);
        if ($btn.hasClass('user-busy')) return;
        $btn.addClass('user-busy');
        $.ajax({
            url: '/manager/users/toggle/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: { user_id: $btn.data('user-id') },
            dataType: 'json'
        }).done(function (res) {
            if (res.ok) {
                var $row = $btn.closest('tr');
                if (res.is_active) {
                    $btn.text('Suspend').removeClass('btn-outline-success').addClass('btn-outline-danger');
                    $row.find('.user-status').html('<span class="status-active">Active</span>');
                } else {
                    $btn.text('Unsuspend').removeClass('btn-outline-danger').addClass('btn-outline-success');
                    $row.find('.user-status').html('<span class="status-suspended">Suspended</span>');
                }
            }
            window.showToast(res.message, res.ok ? 'success' : 'error');
        }).fail(function () {
            window.showToast('Could not update the account.', 'error');
        }).always(function () {
            $btn.removeClass('user-busy');
        });
    });

    // =====================================================================
    // Order management
    // =====================================================================
    var $orderContainer = $('#order-table-container');
    var orderModalEl = document.querySelector('#order-modal');
    var orderModal = orderModalEl ? bootstrap.Modal.getOrCreateInstance(orderModalEl) : null;
    var $orderModalContent = $('#order-modal-content');

    function reloadOrders() {
        $.get('/manager/orders/').done(function (html) {
            $orderContainer.html(html);
        });
    }

    // ---- Open the edit form in the modal ----
    $orderContainer.on('click', '.order-edit', function () {
        $.get('/manager/orders/form/', { order_id: $(this).data('order-id') }).done(function (html) {
            $orderModalContent.html(html);
            orderModal.show();
        }).fail(function () {
            window.showToast('Could not open the order.', 'error');
        });
    });

    // ---- Add / remove item rows inside the modal ----
    $orderModalContent.on('click', '#add-order-item', function () {
        var tmpl = document.querySelector('#new-order-item-template');
        $('#new-order-items').append(tmpl.content.cloneNode(true));
    });

    $orderModalContent.on('click', '.remove-new-order-item', function () {
        $(this).closest('.new-order-item').remove();
    });

    // ---- Submit the edit form ----
    $orderModalContent.on('submit', '#order-form', function (e) {
        e.preventDefault();
        var $submit = $(this).find('button[type="submit"]').prop('disabled', true);
        $.ajax({
            url: '/manager/orders/save/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: $(this).serialize(),
            dataType: 'json'
        }).done(function (res) {
            if (res.ok) {
                orderModal.hide();
                window.showToast(res.message);
                reloadOrders();
            } else if (res.html) {
                $orderModalContent.html(res.html);   // re-render with validation errors
            } else {
                window.showToast(res.message || 'Save failed.', 'error');
                $submit.prop('disabled', false);
            }
        }).fail(function () {
            window.showToast('Save failed. Please try again.', 'error');
            $submit.prop('disabled', false);
        });
    });

    // ---- Delete an order (single confirmation — destructive) ----
    $orderContainer.on('click', '.order-delete', function () {
        var $btn = $(this);
        var id = $btn.data('order-id');
        if (!confirm('Delete order #' + id + '? This cannot be undone.')) return;
        $.ajax({
            url: '/manager/orders/delete/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: { order_id: id },
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
