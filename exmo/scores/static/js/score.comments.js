// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
// Copyright 2010, 2011, 2012 Institute for Information Freedom Development
// Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
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

//  disable all wysiwyg submit buttons
    CKEDITOR.config.extraPlugins = 'onchange';

//  enable submit button if wysiwyg-area not empty
    function ckChangeHandler(e) {
        var sender = e.sender
                , $input = $(sender.container.$)
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
            editor.on('contentDom', function( e ) {
                editor.document.on('keyup', function(event) {
                    ckChangeHandler(e);
                });
            });
        } else {
            editor.on('change', ckChangeHandler);
        }
    }

    for(var name in CKEDITOR.instances) {
        var editor = CKEDITOR.instances[name];
        addContentListener(editor);
        $(editor.element.$).closest('form')
                .children('input[type="submit"]')
                .prop('disabled', true);
    }


//  Open/close comment
    var $anchor = $('a.toggle-comment');

    $anchor.click(function( e ) {
        e.preventDefault();

        var $this = $(this)
            , url = $this.attr('href')
            , pk = $this.attr('rel')
            , openedClass = $this.closest('td').attr('data-class');

        $.ajax({
            type : "POST",
            url: url,
            data : {pk: pk, openedClass: openedClass},
            dataType: "json",
            success: function(data) {
                if (data.success) {
                    $this.html('');
                    if (data.status == 0) {
                        $this.append(gettext('Close without answer'));
                        $this.closest('td').addClass(openedClass);
                    }
                    if (data.status == 2) {
                        $this.append(gettext('Open comment'));
                        $this.closest('td').removeClass(openedClass);
                    }
                }
            }
        });

        return false;
    });

//  Delete claim
    var $claimAnchor = $('a.delete-claim');

    $claimAnchor.click(function( e ) {
        e.preventDefault();

        var $this = $(this)
                , url = $this.attr('href')
                , pk = $this.attr('rel')
                , $container = $this.closest('tr');

        $.ajax({
            type : "POST",
            url: url,
            data : {pk: pk},
            dataType: "json",
            success: function(data) {
                if (data.success) {
                    $container.fadeOut(300, function() {
                        $container.remove();
                    })
                }
            }
        });
        return false;
    });

//  Claim answer
    var $claimAnswerAnchor = $('a.answer-claim')
        , pkClaim = undefined;

    $claimAnswerAnchor.click(function( e ) {
        e.preventDefault();

        var $this = $(this)
            , $form = $('#add-claim').remove();

        $form.addClass('reply-form-tweak');

        if (pkClaim != undefined && pkClaim == $this.attr('rel')) {
            if($form.css('display') == 'block') {
                $form.hide();
            } else {
                $form.show();
            }
        } else {
            $form.show();
        }

        var $container = $this.closest('td');

        pkClaim = $this.attr('rel');

        django_wysiwyg.disable('id_claim-comment_editor');

        $container.append($form);

        var $input = $('#id_claim-claim_id');

        $input.val(pkClaim);

        django_wysiwyg.enable('id_claim-comment_editor', 'id_claim-comment', null);
        addContentListener(CKEDITOR.instances['id_claim-comment']);
    });

//  Clarification answer
    var $clarificationAnswerAnchor = $('a.answer-clarification')
        , pkClarification = undefined;

    $clarificationAnswerAnchor.click(function( e ) {
        e.preventDefault();

        var $this = $(this)
            , $form = $('#add-clarification').remove();

        $form.addClass('reply-form-tweak');

        if (pkClarification != undefined && pkClarification == $this.attr('rel')) {
            if($form.css('display') == 'block') {
                $form.hide();
            } else {
                $form.show();
            }
        } else {
            $form.show();
        }

        var $container = $this.closest('td');

        pkClarification = $this.attr('rel');

        django_wysiwyg.disable('id_clarification-comment_editor');

        $container.append($form);

        var $input = $('#id_clarification-clarification_id');

        $input.val(pkClarification);

        django_wysiwyg.enable('id_clarification-comment_editor', 'id_clarification-comment', null);
        addContentListener(CKEDITOR.instances['id_clarification-comment']);
    })
});
