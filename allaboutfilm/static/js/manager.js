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

    // ---- Employee: edit stock only (reuses the inventory modal) ----
    $container.on('click', '.inventory-stock', function () {
        $.get('/manager/inventory/stock/', { code: $(this).data('code') }).done(function (html) {
            $modalContent.html(html);
            modal.show();
        }).fail(function () {
            window.showToast('Could not open the stock editor.', 'error');
        });
    });

    $modalContent.on('submit', '#stock-form', function (e) {
        e.preventDefault();
        var $submit = $(this).find('button[type="submit"]').prop('disabled', true);
        $.ajax({
            url: '/manager/inventory/stock/save/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: $(this).serialize(),
            dataType: 'json'
        }).done(function (res) {
            if (res.ok) {
                modal.hide();
                window.showToast(res.message);
                reloadTable();
            } else if (res.html) {
                $modalContent.html(res.html);
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

    // ---- Manager: view a customer's pending reports ----
    var reportsModalEl = document.querySelector('#reports-modal');
    var reportsModal = reportsModalEl ? bootstrap.Modal.getOrCreateInstance(reportsModalEl) : null;
    var $reportsModalContent = $('#reports-modal-content');

    $userContainer.on('click', '.report-view', function () {
        $.get('/manager/users/reports/view/', { user_id: $(this).data('user-id') }).done(function (html) {
            $reportsModalContent.html(html);
            reportsModal.show();
        }).fail(function () {
            window.showToast('Could not load the reports.', 'error');
        });
    });

    // ---- Manager: dismiss a customer's pending reports ----
    $userContainer.on('click', '.report-dismiss', function () {
        var id = $(this).data('user-id');
        $.ajax({
            url: '/manager/users/reports/resolve/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: { user_id: id },
            dataType: 'json'
        }).done(function (res) {
            if (res.ok) {
                $userContainer.find('tr[data-user-id="' + id + '"] .user-reports')
                    .html('<span class="text-muted">&mdash;</span>');
            }
            window.showToast(res.message, res.ok ? 'success' : 'error');
        }).fail(function () {
            window.showToast('Could not dismiss the reports.', 'error');
        });
    });

    // ---- Employee: report a customer to the manager ----
    var reportModalEl = document.querySelector('#report-modal');
    var reportModal = reportModalEl ? bootstrap.Modal.getOrCreateInstance(reportModalEl) : null;
    var reportUserId = null;

    $userContainer.on('click', '.user-report-btn', function () {
        reportUserId = $(this).data('user-id');
        $('#report-username').text($(this).data('username'));
        $('#report-reason').val('');
        reportModal.show();
    });

    $('#report-submit').on('click', function () {
        var $btn = $(this).prop('disabled', true);
        $.ajax({
            url: '/manager/users/report/',
            method: 'POST',
            headers: { 'X-CSRFToken': window.getCsrfToken() },
            data: { user_id: reportUserId, reason: $('#report-reason').val() },
            dataType: 'json'
        }).done(function (res) {
            if (res.ok) {
                reportModal.hide();
                var $cell = $userContainer.find('tr[data-user-id="' + reportUserId + '"] .user-reports');
                if ($cell.length) {
                    $cell.html('<span class="badge bg-warning text-dark report-count">' + res.pending + '</span>');
                }
            }
            window.showToast(res.message, res.ok ? 'success' : 'error');
        }).fail(function () {
            window.showToast('Could not submit the report.', 'error');
        }).always(function () {
            $btn.prop('disabled', false);
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
