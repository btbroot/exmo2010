// This file is part of EXMO2010 software.
// Copyright 2013 Al Nikolov
// Copyright 2013 Foundation "Institute for Information Freedom Development"
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

    var $hash = window.location.hash;

    var $comment_field = $("#comment_field");
    var $value = $(".value");
    var $score_table = $(".score-table");

    var $submit_score = $("#submit_scores");
    var $submit_comment = $("#submit_comment");
    var $submit_score_and_comment = $("#submit_score_and_comment");
    var $non_relevant_button = $(".non_relevant_button");

    var $non_edit_table = $(".non_edit_table");
    var $edit_table = $(".edit_table");
    var $part_edit_table = $(".part_edit_table");

    var $tab_content_comments = $('.tab-content-comments');
    var $tab_content_clarifications = $('.tab-content-clarifications');
    var $tab_content_claims = $('.tab-content-claims');

    var $edit_tabs = $('.edit-tabs');


    $non_relevant_button.hide();

    // CKEditor's buttons property (disable/enable)
    CKEDITOR.config.extraPlugins = 'onchange';

    function ckChangeHandler(e) {
        var sender = e.sender,
            $input = $(sender.container.$)
                    .closest('form')
                    .children('input[type="submit"]');
        if(sender.document.getBody().getChild(0).getText()) {
            $input.prop('disabled', false);
        } else {
            $input.prop('disabled', true);
        }
    }

    function addContentListener(editor) {
        if ($.browser.msie) {
            editor.on('contentDom', function(e) {
                editor.document.on('keyup', function() {
                    ckChangeHandler(e);
                });
            });
        } else {
            editor.on('change', ckChangeHandler);
        }
    }

    for(var name in CKEDITOR.instances) {
        if (name=='id_comment') {
            continue;
        }
        var editor = CKEDITOR.instances[name];
        addContentListener(editor);
        $(editor.element.$).closest('form')
                .children('input[type="submit"]')
                .prop('disabled', true);
    }


    // change score handler
    $('input:radio').each(function() {
        $(this).data('initialValue', $(this).serialize());
    });

    var isDirty = false;

    var $cke_comment = CKEDITOR.instances['id_comment'];
    $cke_comment.on('change', function(e) {

        var $cke_text = $cke_comment.document.getBody().getChild(0);
        // special condition for IE and Opera
        if($cke_text && $cke_text.getText() && $cke_text.getText() != String.fromCharCode(10)) {
            $submit_comment.prop('disabled', false);
            if (isDirty) {
                $submit_score_and_comment.prop('disabled', false);
            } else {
                $submit_score_and_comment.prop('disabled', true);
            }
        } else {
            $submit_comment.prop('disabled', true);
            $submit_score_and_comment.prop('disabled', true);
        }
    });

    function scoreChanged() {
        isDirty = false;

        $('input:radio').each(function () {
            if($(this).data('initialValue') != $(this).serialize()) {
                isDirty = true;
            }
        });

        var $cke_field = $cke_comment.document.getBody().getChild(0);

        if(isDirty == true){
            if ($cke_field && $cke_field.getText()) {
                $submit_score_and_comment.prop('disabled',false);
            } else {
                $submit_score_and_comment.prop('disabled',true);
            }
        } else {
            $submit_score_and_comment.prop('disabled',true);
        }
    }

    $("input:radio").on('change', function() {
        scoreChanged();
    });


    // tabs clicking (comment, clarification, claim)
    $('.ccc-tabs').live('click', function(e) {
        var $link;

        switch (e.target.hash) {
           case '#comments':
              $tab_content_clarifications.hide();
              $tab_content_claims.hide();
              $tab_content_comments.show();
              $('.edit-tabs span').removeClass('active');
              $edit_tabs.show();
              break;
           case '#clarifications':
              $tab_content_comments.hide();
              $tab_content_claims.hide();
              $tab_content_clarifications.show();
              $edit_tabs.hide();
              break;
           case '#claims':
              $tab_content_comments.hide();
              $tab_content_clarifications.hide();
              $tab_content_claims.show();
              $edit_tabs.hide();
              break;
        }

        $link = $('a[href="' + e.target.hash + '"]');
        $edit_table.hide();
        $part_edit_table.hide();
        $non_edit_table.show();
        $value.removeClass("blank");
        $score_table.removeClass("editable");
        $score_table.addClass("non-editable");
        $comment_field.hide();
        $submit_score.hide();
        $link.parent().addClass('active').siblings().removeClass('active');
        window.location.hash = '';

        return false;
    });


    // tabs clicking (reply, change score, edit)
    $edit_tabs.live('click', function(e) {
        var $link;

        switch (e.target.hash) {
           case '#reply':
              $comment_field.show();
              $edit_table.hide();
              $part_edit_table.hide();
              $non_edit_table.show();

              $value.removeClass("blank");
              $score_table.removeClass("editable");
              $score_table.addClass("non-editable");

              $submit_score.hide();
              $submit_score_and_comment.hide();
              $submit_comment.show();
              $non_relevant_button.hide();
              break;
           case '#change_score':
              $comment_field.show();
              $non_edit_table.hide();
              $part_edit_table.hide();
              $edit_table.show();

              $value.addClass("blank");
              $score_table.addClass("editable");
              $score_table.removeClass("non-editable");

              $submit_score.hide();
              $submit_comment.hide();
              $submit_score_and_comment.show();
              $non_relevant_button.show();
              break;
           case '#edit':
              $comment_field.hide();
              $non_edit_table.hide();
              $edit_table.hide();
              $part_edit_table.show();

              $value.removeClass("blank");
              $score_table.removeClass("editable");
              $score_table.addClass("non-editable");

              $submit_comment.hide();
              $submit_score_and_comment.hide();
              $submit_score.show();
              $non_relevant_button.show();
              break;
        }

        $link = $('a[href="' + e.target.hash + '"]');
        $link.parent().addClass('active').siblings().removeClass('active');
        $(window).resize();

        return false
    });


    // change tabs if errors exists
    var $error = $('ul.errorlist li').first().text();
    if ($error) {
        $hash = '#change_score';
    }

    $hash && $('a[href="' + $hash + '"]').click();

});

$(window).load(function () {
    $(window).resize();
});
