/* Catalog page: changing the sort dropdown submits the (shared) filter form
 * immediately, so sorting applies at once while keeping the active filters.
 * jQuery + no getElementById. */

$(function () {
    $('#sort-select').on('change', function () {
        this.form.submit();
    });
});
