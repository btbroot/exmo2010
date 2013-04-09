var init_dashboard = function(id, columns, preferences, url) {
    jQuery('#'+id).dashboard({
        'columns': columns,
    });
    jQuery(".group-tabs").tabs();
    jQuery(".group-accordion").accordion({header: '.group-accordion-header'});
};
