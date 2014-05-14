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

    // Switching recommendations and links edit/read modes.
    $('#edit_recommendations, #edit_links').click(function(){
        $(this).closest('div.read_edit').find('.read').hide();
        $(this).closest('div.read_edit').find('.edit').show();
        $(this).hide();
        return false;
    });
    $('a.cancel').click(function(){
        $(this).closest('div.read_edit').find('.edit').hide();
        $(this).closest('div.read_edit').find('.read').show();
        $(this).closest('div.read_edit').find('a').show();
        return false;
    });

    $('#recommendations_form textarea').keyup(function(){
        if (($('.editable-score-table.all_max_initial').length == 0) && ($(this).val().trim() == '')) {
            $('#recommendations_form input[type="submit"]').attr('disabled', true);
        }
        else {
            $('#recommendations_form input[type="submit"]').attr('disabled', false);
        }
    });

    $('#recommendations_form textarea').trigger('keyup');

    // Update recommendations and links after its ajax form submission.
    $('div.read_edit input[type="submit"]').click(function(){
        form = $(this).closest('form');
        $.post(form.attr('action'), form.serialize()).done(function(response){
            read_div = form.closest('div.read_edit').find('.read');
            if (response.data.length == 0) {
                read_div.html(read_div.data('empty_text'));
            }
            else {
                read_div.html(response.data);
            }

            // Update same input in score form.
            var val = form.find('textarea').val();
            var name = form.find('textarea').attr('name');
            $('form.tab_edit').find('textarea[name='+name+']').val(val);
        });
        form.find('a.cancel').click();
        return false;
    });

    function addContentListener(editor, func) {
        if (!editor)
            return;

        if ($.browser.msie) {
            editor.on('contentDom', function( e ) {
                editor.document.on('keyup', function(event) { func(e); });
            });
        } else {
            editor.on('change', func);
        }
    }

    var cke_comment = CKEDITOR.instances['id_comment'];

    // Comment handler should also check if score inputs changed when in edit mode
    addContentListener(cke_comment, function(e) {
        var editor_body = $(e.sender.document.$).find('body');

        if(editor_body && editor_body.text().trim() != '') {
            $("#submit_comment").prop('disabled', false);

            if ($('form div.changed').length > 0) {
                $("#submit_score_and_comment").prop('disabled', false);
            } else {
                $("#submit_score_and_comment").prop('disabled', true);
            }
        } else {
            $("#submit_comment").prop('disabled', true);
            $("#submit_score_and_comment").prop('disabled', true);
        }
        e.sender.updateElement()
    });

    cke_comment.on('instanceReady', function(e){
        $("input:radio:checked").trigger('change');
    });


    function rebuild_bricks() {
        if (!cke_comment.document)
            return;

        all_max = true;  // flag if all radioinputs set to max
        $('input:radio:checked').each(function () {
            if ($(this).val() != $(this).closest('div.table-row').data('max')) {
                all_max = false;
            }
        });

        editor_body = $(cke_comment.document.$).find('body');

        deleteAllAutoScoreCommentBricks();

        if ($('form div.table-row.changed').length > 0) {
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
        }

        $('form div.table-row.changed').each(function() {
            // create brick for each changed input
            input = $(this).find('input:checked');
            initial = input.closest('div.table-row').data('initial');
            newVal = input.val();

            if (initial == '') {initial = 0}
            if (newVal == '') {newVal = '-'}

            label = input.closest('div.table-row').find('div.label').html().trim();
            text = label + ': ' + initial + ' → ' + newVal;

            id = input.attr('name') + '_brick';
            if (editor_body.find('#'+id).length == 0) {
                makeBrick(id, text).insertAfter(editor_body.find('.autoscore:last'));
            } else {
                editor_body.find('#'+id).val(text);
            }
        })
    }

    $("input:radio").on('change', function() {
        initial = $(this).closest('div.table-row').data('initial');
        if ($(this).val() == initial) {
            $(this).closest('div.table-row').removeClass('changed');
        }
        else {
            // changes form '-' to '0' aren't interesting
            if (!((initial == '') && ($(this).val() == '0'))) {
                $(this).closest('div.table-row').addClass('changed');
            }
        }

        rebuild_bricks();
        $('#recommendations_form textarea').trigger('keyup');
        cke_comment.fire('change', cke_comment);
    });

    // create Brick - uneditable block of text inside CKEDITOR
    function makeBrick(id, text, options) {
        defoptions = { class: '', css: { border: 'none', width: '300px', color: 'black', margin: '0px'} };
        options = $.extend(true, defoptions, options);
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
        if (cke_comment.document) {
            $(cke_comment.document.$).find('.autoscore').remove();
            $(cke_comment.document.$).find('#autoscore-break').remove();
        }
    }

    // tabs clicking (reply, edit score)
    $('.reply-edit a').click(function(e) {
        $(".comment-form").show();
        switch (e.target.hash) {
            case '#reply':
                $('.tab_edit').hide();
                $('.tab-reply-block').show();
                deleteAllAutoScoreCommentBricks();
                break;
            case '#change_score':
                $('.tab_edit').show();
                $('.tab-reply-block').hide();
                rebuild_bricks();
                break;
        }

        // BUG 1516: inactive CKEditor.
        // TODO: rewrite for new ckeditor version.
        // $('#cke_contents_id_comment').children()[1].style.width = '100%';

        $('a[href="' + e.target.hash + '"]').parent().addClass('active').siblings().removeClass('active');
        $(window).resize();

        return false;
    });

    // Submit score form with comment.
    $("#submit_score_and_comment").click(function(){
        // convert all bricks to normal text spans before sending comment
        editor_body = $(cke_comment.document.$).find('body');
        editor_body.find('input.autoscore').each(function(){
            repl = '<span>'+$(this).val()+'</span>';
            $(repl).insertAfter($(this));
            $(this).remove();
        });

        cke_comment.updateElement();
        $('form.tab_edit input[name="comment"]').val($('#id_comment').val())
        $('form.tab_edit').submit();
        return false;
    });

    // If form was posted and contain errors - open edit tab.
    if ($('form.tab_edit div.errors li').length) {
        $('a[href="#change_score"]').click();
    }

});
