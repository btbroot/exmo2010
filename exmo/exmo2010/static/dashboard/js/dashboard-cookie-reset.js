function dashboard_reset() {
    $.cookie('admin-tools.exmo2010', null, {path: '/'});
    $('#dashboard_reset').submit();
};
