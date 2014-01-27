// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
// Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
// Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
    // insert loader image
    $('<span/>', {'class': 'rating-ajax'}).insertBefore( '.get-rating' );
    // get rating places
    $.getJSON("/exmo2010/score/rating_update", {task_id: $('#task_id').data('task_id')})
        .done(function(data) {
            $.each(data, function(key, val) {
                if (val) {
                    $('.get-rating').show();
                    $('#' + key).text(val + ' ' + gettext('place'));
                }
            });
            $('.rating-ajax').remove();
        });
});
