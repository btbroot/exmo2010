// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
// Copyright 2010, 2011 Institute for Information Freedom Development
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
    var comment_field = $('div.comment-form').find('textarea');
    var editor = CKEDITOR.instances[comment_field.attr('id')];

    if (editor != undefined) {
        // Update original form inputs when text typed in CKEDITOR
        // Enable submit button if CKEDITOR input not empty.
        function ckChangeHandler(e) {
            var editor_body = $(e.sender.document.$).find('body');

            if(editor_body && editor_body.text().trim() != '') {
                $('#submit_comment').prop('disabled', false);
            } else {
                $('#submit_comment').prop('disabled', true);
            }
            e.sender.updateElement()
        }

        if ($.browser.msie) {
            editor.on('contentDom', function(e) {
                editor.document.on('keyup', function(event) { ckChangeHandler(e); });
            });
        } else {
            editor.on('change', ckChangeHandler);
        }
    } else {
        comment_field.on('change keyup paste', function() {
            if($(this).val().trim() != '') {
                $('#submit_comment').prop('disabled', false);
            } else {
                $('#submit_comment').prop('disabled', true);
            }
        })
    }
});
