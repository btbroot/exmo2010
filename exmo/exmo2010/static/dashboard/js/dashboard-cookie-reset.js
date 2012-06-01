var dashboard_reset = function() {
    $.cookie('admin-tools.exmo2010', null, {path: '/'});
    $('#dashboard_reset').submit();
};
