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

    var $non_editable_table_form = $('#non_editable_table_form');
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

    var $edit_tabs = $('.edit-tabs');


    $non_relevant_button.hide();

    // change score handler
    // save initial values
    var $radioInitial = {};
    $('input:radio').each(function() {
        $(this).data('initialValue', $(this).serialize());
        if ($(this).attr("checked")=="checked") {
            $radioInitial[$(this).attr('name')] = $(this).val();
        }
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


    // overwrite tabs clicking (comment, clarification, claim) from ccc-tabs.js
    $('.ccc-tabs').live('click', function(e) {

        switch (e.target.hash) {
           case '#comments':
              $('.edit-tabs span').removeClass('active');
              $edit_tabs.show();
              break;
           case '#clarifications':
              $edit_tabs.hide();
              break;
           case '#claims':
              $edit_tabs.hide();
              break;
        }

        $edit_table.hide();
        $part_edit_table.hide();
        $non_edit_table.show();
        $value.removeClass("blank");
        $score_table.removeClass("editable");
        $score_table.addClass("non-editable");
        $comment_field.hide();
        $submit_score.hide();

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
              $submit_score.prop('disabled',false).show();
              $non_relevant_button.show();
              break;
        }

        $link = $('a[href="' + e.target.hash + '"]');
        $link.parent().addClass('active').siblings().removeClass('active');
        $(window).resize();

        return false
    });


    // submit form
    // returns radio buttons initial values
    function clearRadio() {
        $('input:radio').each(function () {
            $(this).prop('checked', !!($(this).val() == $radioInitial[$(this).attr('name')]));
        });
    }

    $submit_score.click(function(){
        $cke_comment.setData('');
        clearRadio();
    });

    $submit_comment.mousedown(function(){
        $non_editable_table_form.get(0).reset();
    });


    // change tabs if errors exists
    var $error = $('ul.errorlist li').first().text();
    if ($error) {
        window.location.hash = '#change_score';
    }

});

$(window).load(function () {
    $(window).resize();
});
