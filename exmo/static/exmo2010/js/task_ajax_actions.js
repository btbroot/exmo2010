// This file is part of EXMO2010 software.
// Copyright 2015 IRSI LTD
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
$(function(){
    function show_status_actions(td) {
        $(td).children('img').hide();  // hide "loading..." image
        $(td).children('.task_status_display').show();
        var perms = $(td).data('perms').split(' ');
        for (var i = 0; i < perms.length; i++) {
            action_class = '.perms_' + perms[i];
            $(td).find(action_class).show();  // show permitted action
        }
    }

    $('td.task-status').each(function(){show_status_actions(this)});

    $(document).on('click', 'td.task-status a', function () {
        var td = $(this).closest('td');
        td.children().hide().filter('img').show();  // hide contents, show "loading..." image
        $.post($(this).attr('href'))
            .done(function(new_data) {
                td.data('perms', new_data.perms);
                td.children('.task_status_display').html(new_data.status_display);
                show_status_actions(td);
            })
            .fail(function() {
                // Permision denied or error
                show_status_actions(td);  // just show previous state
            });
        return false;
    });
});
