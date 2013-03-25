// This file is part of EXMO2010 software.
// Copyright 2010, 2011 Al Nikolov
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

$("#id_comment_notification_type").live('change', function () {

    if ($(this).val() == '0') {
        $("#id_notify_on_all_comments, #id_notify_on_my_comments").attr("disabled", true).attr("checked", false);
    } else {
        $("#id_notify_on_all_comments, #id_notify_on_my_comments").removeAttr("disabled");
    }

    if ($(this).val() == '2') {
        $("#cnd").show();
    }
    else {
        $("#cnd").hide();
    }
});
$("#id_score_notification_type").live('change', function () {
    if ($(this).val() == '2') {
        $("#snd").show();
    }
    else {
        $("#snd").hide();
    }
});


$(function () {
        if ($("#id_comment_notification_type").val() != '2') {
            $("#cnd").hide();
        }
        if ($("#id_score_notification_type").val() != '2') {
            $("#snd").hide();
        }

    }
);
