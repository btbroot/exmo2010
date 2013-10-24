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

$(document).ready(function () {

    var $comment_type = $("#id_notification_type");
    var $interval = $("#id_notification_interval");
    var $notification_self = $("#id_notification_self");

    function notification_form(value) {
        switch(value){
            case '0':
                $notification_self.attr("disabled", true).attr("checked", false);
                $interval.hide();
                break;
            case '1':
                $notification_self.removeAttr("disabled");
                $interval.hide();
                break;
            case '2':
                $notification_self.removeAttr("disabled");
                $interval.show();
                break;
        }
    }

    notification_form($comment_type.val());

    $comment_type.change(function () {
        notification_form($(this).val());
    });

});
