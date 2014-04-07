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

    $('textarea[name="recommendations"]').autosize()
    $('textarea[name="links"]').autosize()


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


    //  Claim answer
    var pkClaim = undefined;

    $('a.answer-claim').click(function( e ) {
        e.preventDefault();

        var $form = $('#add-claim').remove();

        $form.addClass('reply-form-tweak');

        if (pkClaim != undefined && pkClaim == $(this).attr('rel')) {
            if($form.css('display') == 'block') {
                $form.hide();
            } else {
                $form.show();
            }
        } else {
            $form.show();
        }

        pkClaim = $(this).attr('rel');

        $(this).closest('td').append($form);

        $('#id_claim-claim_id').val(pkClaim);

        addContentListener(CKEDITOR.instances['id_claim-comment']);
    });


    //  Clarification answer
    var pkClarification = undefined;

    $('a.answer-clarification').click(function( e ) {
        e.preventDefault();

        var $form = $('#add-clarification').remove();

        $form.addClass('reply-form-tweak');

        if (pkClarification != undefined && pkClarification == $(this).attr('rel')) {
            if($form.css('display') == 'block') {
                $form.hide();
            } else {
                $form.show();
            }
        } else {
            $form.show();
        }

        pkClarification = $(this).attr('rel');

        $(this).closest('td').append($form);

        $('#id_clarification-clarification_id').val(pkClarification);

        addContentListener(CKEDITOR.instances['id_clarification-comment']);
    });

    // Open/close comment
    $('a.toggle-comment').click(function( e ) {
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
