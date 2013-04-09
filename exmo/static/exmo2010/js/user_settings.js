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

$(document).ready(function () {

    var $comment_type = $("#id_comment_notification_type");
    var $score_type = $("#id_score_notification_type");
    var $comments = $("#id_notify_on_all_comments, #id_notify_on_my_comments");
    var $all_comments = $("#id_notify_on_all_comments");
    var $cnd = $("#cnd");
    var $snd = $("#snd");

    switch($comment_type.val()){
        case '0':
            $comments.attr("disabled", true).attr("checked", false);
            $cnd.hide();
            break;
        case '1':
            $cnd.hide();
            break;
        case '2':
            $all_comments.attr("disabled", true).attr("checked", false);
            break;
    }

    if ($score_type.val() != '2') {
        $snd.hide();
    }

    $comment_type.change(function () {

        switch($(this).val()){
            case '0':
                $comments.attr("disabled", true).attr("checked", false);
                $cnd.hide();
                break;
            case '1':
                $comments.removeAttr("disabled");
                $cnd.hide();
                break;
            case '2':
                $comments.removeAttr("disabled");
                $all_comments.removeAttr("disabled").attr("disabled", true).attr("checked", false);
                $cnd.show();
                break;
        }

    });

    $score_type.change(function () {

        if ($(this).val() == '2') {
            $snd.show();
        }
        else {
            $snd.hide();
        }

    });

});
