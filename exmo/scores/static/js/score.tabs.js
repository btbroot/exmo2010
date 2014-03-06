// This file is part of EXMO2010 software.
// Copyright 2013 Al Nikolov
// Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
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

    var $submits = $('input[type=submit]');
    var $submit_score = $("#submit_scores");
    var $submit_comment = $("#submit_comment");
    var $submit_score_and_comment = $("#submit_score_and_comment");
    var $non_relevant_button = $(".non_relevant_button");

    var $non_edit_table = $(".non_edit_table");
    var $edit_table = $(".edit_table");
    var $part_edit_table = $(".part_edit_table");

    var $edit_tabs = $('.edit-tabs');
    var $tabs = $('input[name=tabs]:hidden');

    $non_relevant_button.hide();

    // change score handler
    // save initial values
    var $radioInitial = {};
    var $radioValues = {};
    var $radioLabels = {};
    var $radioMax = {};
    $('input:radio').each(function() {
        if (!($(this).attr('name') in $radioValues)) {
            $radioValues[$(this).attr('name')] = [];
        }
        if (!isNaN(parseInt($(this).val()))) {
            $radioValues[$(this).attr('name')].push(parseInt($(this).val()));
        }
        if ($(this).attr("checked")=="checked") {
            $radioInitial[$(this).attr('name')] = $(this).val();
        }
    });

    for (var key in $radioValues) {
        // get maximum possible value for each radio input
        $radioMax[key] = Math.max.apply(null, $radioValues[key]);
        // get text label for each radio input
        $radioLabels[key] = $('input[name='+key+']').closest('td').prev().find('label').html().trim();
    }

    var isDirty = false;

    var $cke_comment = CKEDITOR.instances['id_comment'];
    $cke_comment.on('change', function(e) {
        editor_body = $($cke_comment.document.$).find('body');

        if(editor_body && editor_body.text().trim() != '') {
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
        changedVals = {};
        all_max = true;  // flag if all radioinputs set to max
        $('input:radio:checked').each(function () {
            val = $(this).val()
            name = $(this).attr('name')
            initial = $radioInitial[name];
            if (parseInt(val) != $radioMax[name]) {
                all_max = false;
            }
            if (val != initial) {
                isDirty = true;
                if ((initial == '') && (val == '0')) {
                    // changes form '-' to '0' aren't interesting
                    return;
                }
                changedVals[name] = val;
            }
        });

        editor_body = $($cke_comment.document.$).find('body');

        deleteAllAutoScoreCommentBricks();

        if (!$.isEmptyObject(changedVals)) {
            // create introduction text
            if (all_max == true) {
                text = gettext("Score changed to maximum");
                makeBrick('autoscore-intro', text, {class:'max'}).prependTo(editor_body);
            } else {
                text = gettext("Score changed");
                makeBrick('autoscore-intro', text).prependTo(editor_body);
            }
            // create guard break
            $('<br id="autoscore-break" />').insertAfter(editor_body.find('.autoscore:last'));

            for (var name in changedVals) {
                // create brick for each changed input
                id = name + '_brick';
                initial = $radioInitial[name];
                newVal = changedVals[name];

                if (initial == '') {
                    initial = 0
                }
                if (newVal == '') {
                    newVal = '-'
                }
                text = $radioLabels[name] + ': ' + initial + ' → ' + newVal;
                if (editor_body.find('#'+id).length == 0) {
                    makeBrick(id, text).insertAfter(editor_body.find('.autoscore:last'));
                } else {
                    editor_body.find('#'+id).val(text);
                }
            }
        }

        if(isDirty == true){
            if (editor_body && editor_body.text()) {
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

    // create Brick - uneditable block of text inside CKEDITOR
    function makeBrick(id, text, options) {
        defoptions = {
            css: {
                border: 'none',
                width: '300px',
                color: 'black',
                margin: '0px' },
            class: ''
        }
        options = $.extend(true, defoptions, options)
        return $(
            '<input>',
            {
                id: id,
                class: 'autoscore ' + options.class,
                css: options.css,
                val: text,
                disabled: 'disabled'
            }).add('<br class="autoscore" />')
    }

    function deleteAllAutoScoreCommentBricks(){
        // if CKEditor instance is not ready, skip this part
        if ($cke_comment.document) {
            $($cke_comment.document.$).find('.autoscore').remove();
            $($cke_comment.document.$).find('#autoscore-break').remove();
        }
    }

    // TICKET 1516: inactive CKEditor
    function redraw_ckeditor_width(editor) {
        var iframe = $('#cke_contents_' + editor).children()[1];
        if (iframe) {
            iframe.style.width = '100%';
        }
    }

    // overwrite tabs clicking (comment, clarification, claim) from ccc-tabs.js
    $('.ccc-tabs').live('click', function(e) {
        var editor;
        deleteAllAutoScoreCommentBricks();

        switch (e.target.hash) {
           case '#comments':
              $('.edit-tabs span').removeClass('active');
              $edit_tabs.show();
              editor = 'id_comment';
              break;
           case '#clarifications':
              $edit_tabs.hide();
              editor = 'id_clarification-comment';
              break;
           case '#claims':
              $edit_tabs.hide();
              editor = 'id_claim-comment';
              break;
        }

        redraw_ckeditor_width(editor);
        $edit_table.hide();
        $part_edit_table.hide();
        $non_edit_table.show();
        $value.removeClass("blank");
        $score_table.removeClass("editable");
        $score_table.addClass("non-editable");
        $non_relevant_button.hide();
        $comment_field.hide();
        $submit_score.hide();

        return false;
    });


    // tabs clicking (reply, change score, edit)
    $edit_tabs.live('click', function(e) {
        var $link;
        deleteAllAutoScoreCommentBricks();

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
              scoreChanged();
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

        redraw_ckeditor_width('id_comment');
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

    $submit_score_and_comment.mousedown(function(){
        // convert all bricks to normal text spans before sending comment
        editor_body = $($cke_comment.document.$).find('body');
        editor_body.find('input.autoscore').each(function(){
            repl = '<span>'+$(this).val()+'</span>';
            $(repl).insertAfter($(this))
            $(this).remove();
        })
    })

    $submits.mousedown(function(e){
        $tabs.val(e.target.name);
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
