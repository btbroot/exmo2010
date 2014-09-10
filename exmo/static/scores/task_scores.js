// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
// Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
// Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
// Copyright 2014 IRSI LTD
//
//    This program is free software: you can redistribute it and/or modify
//    it under the terms of the GNU Affero General Public License as
//    published by the Free Software Foundation, either version 3 of the
//    License, or (at your option) any later version.
//
//    This program is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU Affero General Public License for more details.
//
//    You should have received a copy of the GNU Affero General Public License
//    along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
$(document).ready(function() {

    /* Tables sorting */

    $(".relevant-params-table").tablesorter();
    $(".nonrelevant-params-table").tablesorter();

    /* Rating place */

    var rating_data = $('#rating_data');
    if(rating_data.length) {
        // insert loader image
        $('<span class="rating-ajax" />').insertBefore('#rating_place');
        // get rating place
        var url = rating_data.data('url');
        var task_id = rating_data.data('task_id');
        $.getJSON(url, { task_id: task_id })
            .done(function(data) {
                var val = data['rating_place'];
                if (val) {$('#rating_place').text(val + ' ' + gettext('place')).show();}
                $('.rating-ajax').remove();
        });
    }

    /* One-click upload */

    var upload_link = $('#upload_link');
    if(upload_link.length) {
        upload_link.click(function() {
            $('#upload_form input[type="file"]').click();
            return false
        });

        $('#upload_form').change(function () {
            this.submit();
        });
    }

    /* Modal window */

    $(document).on('mousewheel', '.simplemodal-overlay, .simplemodal-data', function() {
        return false;
    });

    $(".modal-open").click(function(e) {
        $("#modal_window").modal({
            overlayClose: true,
            onClose: $.modal.close()
        });
        e.preventDefault();
    });

    $("#cancel_link").click(function(e) {
        $.modal.close();
        e.preventDefault();
    });
});
