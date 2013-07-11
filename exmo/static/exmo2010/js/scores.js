// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
// Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
// Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
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
    var $rating_names = [];
    var $result = {};

    $.ajaxSetup({
        traditional: true
    });

    var $task_id = $('#place').data('task_id');
    if ($task_id) {
        $result['task_id'] = $task_id;
        $('.get-rating').each(function(){
            $rating_names.push($(this).attr('id'));
        });
        $result['rating_names'] = $rating_names;

        $.getJSON("/exmo2010/score/rating_update", $result)
            .success(function(data) {
                $.each(data, function(key, val) {
                    var $key = '#' + key;
                    if (val) {
                        $($key).show();
                        $($key + '_span').text(val + ' ' + gettext('place'));
                    }
                    $($key + '_img').remove();
                });
            });
    }

});
