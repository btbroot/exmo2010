// This file is part of EXMO2010 software.
// Copyright 2014 Foundation "Institute for Information Freedom Development"
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

    if (Object.keys(CKEDITOR.instances).length) {
        $.each(CKEDITOR.instances, function(id, editor){
            if (editor != undefined) {
                // Update original form inputs when text typed in CKEDITOR
                // Enable submit button if CKEDITOR input not empty.
                function ckChangeHandler(e) {
                    var editor_body = $(e.sender.document.$).find('body');
                    var submit = $(e.sender.element.$).closest('form').find('input[type=submit]');

                    if(editor_body && editor_body.text().trim() != '') {
                        submit.prop('disabled', false);
                    } else {
                        submit.prop('disabled', true);
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
            }
        });
    } else {
        $('div.comment-form').find('textarea').each(function(){
            $(this).on('change keyup paste', function() {
                var submit = $(this).closest('form').find('input[type=submit]');
                if($(this).val().trim() != '') {
                    submit.prop('disabled', false);
                } else {
                    submit.prop('disabled', true);
                }
            })
        });
    }

    $('a[href="#show_grounds"]').click(function(e){
        $(e.target).siblings('.grounds').slideToggle(function(){
            $(e.target).hide().siblings('a[href="#hide_grounds"]').show();
        });
        return false;
    });
    $('a[href="#hide_grounds"]').click(function(e){
        $(e.target).siblings('.grounds').slideToggle(function(){
            $(e.target).hide().siblings('a[href="#show_grounds"]').show();
        });
        return false;
    });

    $('div.recommendations-block tr').each(function(){
        var len, tr = $(this);
        var comments = tr.find('div.comment');
        if (tr.hasClass('nonrelevant') || tr.hasClass('finished')) {
            // Nonrelevant and finished will collapse all comments.
            len = comments.length;
        }
        else {
            // Relevant scores will collapse all except 2 last comments.
            len = comments.length - 2;
        }
        for (var i=0; i<len; i++) {
            $(comments[i]).addClass('collapsible').hide();
        }
    });

    $('.comment-toggle').click(function(){
        var tr = $(this).closest('tr');
        tr.find('.collapsible').toggle();
        tr.find('.comment-toggle').toggle();
        if (tr.hasClass('finished')) {
            tr.find('div.comment-form').toggle()
        }
    });

    $('input.fake_input').click(function(){
        var div = $(this).hide().closest('div.comment-form').find('div');
        var comment_area = div.find('textarea');
        var cke_area = CKEDITOR.instances[comment_area.attr('id')];
        div.show();
        cke_area != undefined ? cke_area.focus() : comment_area.focus();
    })
});
