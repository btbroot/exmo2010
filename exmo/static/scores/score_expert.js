// This file is part of EXMO2010 software.
// Copyright 2013 Al Nikolov
// Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
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

$(document).ready(function() {
    var settings = {append: ''};  // remove new line

    $('textarea[name="recommendations"]').autosize(settings);
    $('textarea[name="links"]').autosize(settings);

    // Prevent '-' radiobutton from being selected on click.
    $(".editable-score-table li label").on('click', function() {
        if ($(this).find('input').val() == '') {
            return false;
        }
    });

    // Colorize selected criterion radiobuttons on change.
    $("input:radio").on('change', function() {
        var max = $(this).closest('.table-row').data('max');

        // Remove selected classes from all radiobuttons of this criterion.
        $(this).closest('ul').find('li').removeClass('selected').removeClass('selected_max');
        if ($(this).val() == max) {
            $(this).closest('li').addClass('selected_max');
        }
        else {
            $(this).closest('li').addClass('selected');
        }
    });

    // Clicking 'found' criterion should hide and colorize other criteria
    $("input[name='found']").on('change', function() {
        if ($(this).val() == '1') {
            $(".editable-score-table li").each(function() {
                $(this).removeClass('found_0_frozen_red').show();
                if ($(this).find('input').attr('name') != 'found') {
                    $(this).find('input').prop('disabled', false);
                    // Trigger change event to restore autoscore comments for previously
                    // changed criterion.
                    $(this).find('input:checked').trigger('change');
                }
            })
        }
        else {
            $(".editable-score-table li").each(function() {
                if ($(this).find('input').attr('name') != 'found') {
                    $(this).find('input').prop('disabled', true);
                    // Remove 'changed' flag from criterion to prevent autoscore comment generation.
                    $(this).closest('div.table-row').removeClass('changed');
                    $(this).addClass('found_0_frozen_red');

                    if ($(this).find('input').val() != '') {
                        $(this).hide();
                    }
                }
            });
        }
    });

    // Trigger change event to initially colorize radiobuttons
    $("input:radio:checked").trigger('change');


    // Update original form inputs when text typed in CKEDITOR
    // Enable submit button if CKEDITOR input not empty.
    function ckChangeHandler_simple(e) {
        var submit = $(e.sender.container.$).closest('form').find('input[type="submit"]');
        var editor_body = $(e.sender.document.$).find('body');

        if(editor_body && $.trim(editor_body.text()) != '') {
            submit.prop('disabled', false);
        } else {
            submit.prop('disabled', true);
        }
        e.sender.updateElement()
    }

    function addContentListener(editor, func) {
        if (!editor)
            return;

        if ($.browser.msie) {
            // TODO: do we really need this case for IE? Ckeditor dropped support for IE<=8
            editor.on('contentDom', function( e ) {
                editor.document.on('keyup', function(event) { func(e); });
            });
        } else {
            editor.on('change', func);
        }
    }

    addContentListener(CKEDITOR.instances['id_claim-comment'], ckChangeHandler_simple);
    addContentListener(CKEDITOR.instances['id_clarification-comment'], ckChangeHandler_simple);

    // Clarification/Claim tabs clicking
    $('.tabs a').click(function(e) {
        switch (e.target.hash) {
           case '#clarifications':
              $('.tab-content-claims').hide();
              $('.tab-content-clarifications').show();
              break;
           case '#claims':
              $('.tab-content-clarifications').hide();
              $('.tab-content-claims').show();
              break;
        }

        // BUG 1516: inactive CKEditor.
        $('.cke_contents.cke_reset').each(function(){ this.style.width = '100%'; });

        $('a[href="' + e.target.hash + '"]').parent().addClass('active').siblings().removeClass('active');
        return false;
    });

    //  Delete claim
    $('a.delete-claim').click(function() {
        var tr = $(this).closest('tr');

        $.ajax({
            type : "POST",
            url: $(this).attr('href'),
            data : {pk: $(this).attr('rel')},
            dataType: "json",
            success: function(data) {
                if (data.success) {
                    tr.fadeOut(300, function() { tr.remove(); })
                }
            }
        });
        return false;
    });

    //  Claim/Clarification answer
    $('a.answer_form_toggle').click(function() {
        $(this).closest('table').find('.answer_form').hide();
        $(this).closest('td').find('.answer_form').show();

        var editor = CKEDITOR.instances['id_' + $(this).data('prefix') + '-answer'];
        addContentListener(editor, ckChangeHandler_simple);
        return false;
    });

    // Open/close comment
    $('.toggle-comment-container a').click(function( e ) {
        e.preventDefault();

        var $this = $(this);
        var td = $this.closest('td');
        if (td.data('orig_class') == undefined) {
            // save original class
            td.data('orig_class', td.attr('class'));
        }

        $.ajax({
            type: "POST",
            url: $this.attr('href'),
            data: {pk: $this.attr('rel')},
            dataType: "json",
            success: function(data) {
                if (data.success) {
                    $this.html('');
                    if (data.status == 0) {
                        $this.append(gettext('Close without answer'));
                        td.addClass(td.data('orig_class'));
                        td.removeClass('toggled');  // This class used for unit-test only
                    }
                    if (data.status == 2) {
                        $this.append(gettext('Open comment'));
                        td.removeClass(td.data('orig_class'));
                        td.addClass('toggled');  // This class used for unit-test only
                    }
                }
            }
        });

        return false;
    });


    // if monitoring is INTERACTION
    if ($('.reply-edit').length) {
        // Switching recommendations and links edit/read modes.
        $('#edit_recommendations, #edit_links').click(function(){
            $(this).closest('div.read_edit').find('.read').hide();
            $(this).closest('div.read_edit').find('.edit').show();
            $(this).hide();
            $('textarea').trigger('autosize.resize');
            return false;
        });
        $('a.cancel').click(function(){
            $(this).closest('div.read_edit').find('.edit').hide();
            $(this).closest('div.read_edit').find('.read').show();
            $(this).closest('div.read_edit').find('a').show();
            return false;
        });

        var recommendations = $('#recommendations_form textarea');
        recommendations.keyup(function(){
            var is_disabled = ($('.editable-score-table.recommendations_required').length != 0) && ($.trim($(this).val()) == '');
            $('#recommendations_form input[type="submit"]').attr('disabled', is_disabled);
        });

        recommendations.trigger('keyup');

        // Update recommendations and links after its ajax form submission.
        $('div.read_edit input[type="submit"]').click(function(){
            var form = $(this).closest('form');
            $.post(form.attr('action'), form.serialize())
            .done(function(response){
                var read_div = form.closest('div.read_edit').find('.read');
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
                form.find('a.cancel').click();
            })
            .fail(function() {
                alert(gettext('Score is invalid, recommendation can not be changed.'))
            });
            return false;
        });

        if (!CKEDITOR.env.isCompatible) {
            alert(gettext('Your browser is not supported'));
        }
        else {
            var comment_field_id = $('div.comment-form').find('textarea').attr('id');
            var cke_comment = CKEDITOR.instances[comment_field_id];

            cke_comment.on('instanceReady', function (e) {
                // Comment handler should also check if score inputs changed when in edit mode
                addContentListener(cke_comment, function (e) {
                    var editor_body = $(e.sender.document.$).find('body');

                    if (editor_body && $.trim(editor_body.text()) != '') {
                        $("#submit_comment").prop('disabled', false);

                        var is_disabled = $('form div.changed').length == 0;
                        $("#submit_score_and_comment").prop('disabled', is_disabled);
                    } else {
                        $("#submit_comment").prop('disabled', true);
                        $("#submit_score_and_comment").prop('disabled', true);
                    }
                    e.sender.updateElement()
                });

                $("input:radio:checked").trigger('change');
            });


            function rebuild_bricks() {
                if (!cke_comment.document)
                    return;

                var all_max = true;  // flag if all radioinputs set to max
                $('input:radio:checked').each(function () {
                    if ($(this).val() != $(this).closest('div.table-row').data('max')) {
                        all_max = false;
                    }
                });

                var editor_body = $(cke_comment.document.$).find('body');

                deleteAllAutoScoreCommentBricks();

                if ($('form div.table-row.changed').length > 0) {
                    var p = $(editor_body).find('#autoscore_p');
                    if (p.length == 0) {
                        p = $('<p id="autoscore_p" />').prependTo(editor_body);
                    }
                    // Create introduction text
                    if (all_max == true) {
                        makeBrick('autoscore-intro', gettext("Score changed to maximum"), {class: 'max'}).prependTo(p);
                    } else {
                        makeBrick('autoscore-intro', gettext("Score changed")).prependTo(p);
                    }
                    // Create additional paragraph under autoscores block
                    if ($(editor_body).find('p:not(#autoscore_p)').length == 0) {
                        $('<p><br/></p>').insertAfter(p);
                    }
                }

                $('form div.table-row').each(function () {
                    var input = $(this).find('input:checked');
                    var initial = input.closest('div.table-row').data('initial');

                    // if initial is '', display '-'
                    if (initial.length == 0) {
                        initial = '-'
                    }

                    var newVal = input.is(':disabled') ? '-' : input.val();

                    if (newVal == initial) {
                        return;
                    }

                    var label = $.trim(input.closest('div.table-row').find('div.label').html());
                    var text = label + ': ' + initial + ' → ' + newVal;

                    var id = input.attr('name') + '_brick';
                    if (editor_body.find('#' + id).length == 0) {
                        makeBrick(id, text).insertAfter(editor_body.find('.autoscore:last'));
                    } else {
                        editor_body.find('#' + id).val(text);
                    }

                })
            }

            $("input:radio").on('change', function () {
                var initial = $(this).closest('div.table-row').data('initial');
                if ($(this).val() == initial) {
                    $(this).closest('div.table-row').removeClass('changed');
                }
                else {
                    $(this).closest('div.table-row').addClass('changed');
                }

                rebuild_bricks();
                $('#recommendations_form textarea').trigger('keyup');
                cke_comment.fire('change', cke_comment);
            });

            // create Brick - uneditable block of text inside CKEDITOR
            function makeBrick(id, text, options) {
                var defoptions = { class: '', css: { border: 'none', width: '300px', color: 'black', margin: '0px'} };
                var options = $.extend(true, defoptions, options);
                return $(
                    '<input>',
                    {
                        id: id,
                        class: 'autoscore ' + options.class,
                        css: options.css,
                        value: text,
                        disabled: 'disabled'
                    }).add('<br class="autoscore" />')
            }

            function deleteAllAutoScoreCommentBricks() {
                // if CKEditor instance is not ready, skip this part
                if (cke_comment.document) {
                    $(cke_comment.document.$).find('.autoscore').remove();
                }
            }

            // tabs clicking (reply, edit score)
            $('.reply-edit a').click(function (e) {
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
                $('.cke_contents.cke_reset').each(function(){ this.style.width = '100%'; });

                $('a[href="' + e.target.hash + '"]').parent().addClass('active').siblings().removeClass('active');
                $(window).resize();

                return false;
            });

            // Submit score form with comment.
            $("#submit_score_and_comment").click(function () {
                cke_comment.updateElement();
                $('form.tab_edit input[name="' + comment_field_id.slice(3) + '"]').val($('#' + comment_field_id).val());
                $('form.tab_edit').submit();
                return false;
            });
        }

        // If form was posted and contain errors - open edit tab.
        if ($('form.tab_edit div.errors li').length) {
            $('a[href="#change_score"]').click();
        }

        window.score_expert_interaction_loaded = true;
    }
});

$(window).load(function(){
    // Activate claim/clarification or edit tab if url has hash part
    window.location.hash && $('a[href="' + window.location.hash + '"]').click();
});
