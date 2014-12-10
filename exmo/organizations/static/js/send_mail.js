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

$(document).ready(function () {
    // When group checkbox clicked, toggle all children
    $("div.destination input.group").click(function () {
        $(this).closest('div.destination').find('input').prop('checked', $(this).prop('checked'));
    });

    if (CKEDITOR.env.isCompatible) {
        $('input[type="submit"]').prop('disabled', true);
        var editor = CKEDITOR.instances['id_comment'];

        $("div.destination input").click(function () {
            // When children checkbox unchecked, uncheck group checkbox too
            if ($(this).prop('checked') == false) {
                $(this).closest('div.destination').find('input.group').prop('checked', false);
            }
            // Trigger ckeditor change to handle disabling submit button.
            editor.fire('change');
        });

        $("#id_subject").on('keyup', function () {
            // Trigger ckeditor change to handle disabling submit button.
            editor.fire('change');
        });

        CKEDITOR.instances['id_comment'].on('change', function (e) {
            // Update original form input when text typed in CKEDITOR
            e.sender.updateElement();

            // Disable submit button if required inputs are not provided.
            var checked = $('div.org-email-form').find('input:checked');
            var body_text = $.trim($("#id_comment").val());
            var subject_text = $.trim($("#id_subject").val());
            if ((checked.length == 0) || body_text == '' || subject_text == '') {
                $('input[type="submit"]').prop('disabled', true);
            }
            else {
                $('input[type="submit"]').prop('disabled', false);
            }
        });

        editor.fire('change');
    }
});