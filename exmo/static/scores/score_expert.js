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

    $('textarea[name="recommendations"]').autosize();
    $('textarea[name="links"]').autosize();

    // Prevent '-' radiobutton from being selected on clik.
    $(".editable-score-table li label").on('click', function() {
        if ($(this).find('input').val() == '') {
            return false;
        }
    });

    // Colorize selcted criterion radiobuttons on change.
    $("input:radio").on('change', function() {
        max = $(this).closest('.table-row').data('max');

        // Remove selected classes from all radiobuttons of this criterion.
        $(this).closest('ul').find('li').removeClass('selected').removeClass('selected_max');
        if ($(this).val() == max) {
            $(this).closest('li').addClass('selected_max');
        }
        else {
            $(this).closest('li').addClass('selected');
        }
    });

    // Clicking 'found' criterion should hide and colorize other criterions
    $("input[name='found']").on('change', function() {
        if ($(this).val() == '1') {
            $(".editable-score-table li").each(function() {
                $(this).removeClass('found_0_frozen_red').show()
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

        if(editor_body && editor_body.text().trim() != '') {
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
            editor.on('contentDom', function( e ) {
                editor.document.on('keyup', function(event) { func(e); });
            });
        } else {
            editor.on('change', func);
        }
    }

    addContentListener(CKEDITOR.instances['id_claim-comment'], ckChangeHandler_simple)
    addContentListener(CKEDITOR.instances['id_clarification-comment'], ckChangeHandler_simple)

    // Clarification/Claim tabs clicking
    $('.ccc-tabs a').click(function(e) {
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
        // TODO: rewrite for new ckeditor version.
//         $('#cke_contents_id_clarification-comment').children()[1].style.width = '100%';
//         $('#cke_contents_id_claim-comment').children()[1].style.width = '100%';

        $('a[href="' + e.target.hash + '"]').parent().addClass('active').siblings().removeClass('active');
        return false;
    });

    //  Delete claim
    $('a.delete-claim').click(function() {
        tr = $(this).closest('tr');

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
        $(this).closest('table').find('.answer_form').hide()
        $(this).closest('td').find('.answer_form').show()

        var editor = CKEDITOR.instances['id_' + $(this).data('prefix') + '-answer'];
        addContentListener(editor, ckChangeHandler_simple);
        return false;
    });

    // Open/close comment
    $('.toggle-comment-container a').click(function( e ) {
        e.preventDefault();

        var $this = $(this)
        var td = $this.closest('td')
        if (td.data('orig_class') == undefined) {
            // save original class
            td.data('orig_class', td.attr('class'));
        }

        $.ajax({
            type : "POST",
            url: $this.attr('href'),
            data : {pk: $this.attr('rel')},
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

});

$(window).load(function(){
    // Activate claim/clarification or edit tab if url has hash part
    window.location.hash && $('a[href="' + window.location.hash + '"]').click();
})
