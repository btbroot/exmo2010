// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
// Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
// Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
$(document).ready(function () {
    var hash = window.location.hash;

    $('.org-tabs a').click(function(e) {
        $('.tab-content').find(e.target.hash).show().siblings().hide();
        $('a[href="' + e.target.hash + '"]').parent().addClass('active').siblings().removeClass('active');
    });

    hash && $('a[href="' + hash + '"]').click();

    $("td.pseudo").click(function( e ) {
        $(this).children('div.preview-container').toggle();
        $(this).children('div.hidden').toggle();
    });

    // calendar initializing
    var settings = $.datepicker.regional[$('html').attr('lang')];
    settings['numberOfMonths'] = 3;
    settings['showCurrentAtPos'] = 1;
    $('input[name="date_filter_history"]').datepicker(settings);

    function helptextHandler( e ) {
        var top = $(e.target).position().top;
        var left = $(e.target).position().left + $(e.target).width() + 15;
        $('#help-text').show();
        $('#help-text').css('top', top);
        $('#help-text').css('left', left);
        $('.alert-info').hide();
        $(e.data.p).show();
    }

    $("#id_org-email").focusin({p: '#help-emails'}, helptextHandler);
    $("#id_org-phone").focusin({p: '#help-phones'}, helptextHandler);

    $("input[type='text']").focusout(function(){
        $('#help-text').hide();
    });

    // When group checkbox clicked, toggle all children
    $("div.destination input.group").click(function(){
        $(this).closest('div.destination').find('input').prop('checked', $(this).prop('checked'));
    });

    var editor = CKEDITOR.instances['id_comment'];

    $("div.destination input").click(function(){
        // When children checkbox unchecked, uncheck group checkbox too
        if ($(this).prop('checked') == false) {
            $(this).closest('div.destination').find('input.group').prop('checked', false);
        }
        // Trigger ckeditor change to handle disabling submit button.
        editor.fire('change');
    });

    $("#id_subject").on('keyup', function () {
        // Trigger ckeditor change to handle disabling submit button.
        editor.fire('change');
    });

    CKEDITOR.instances['id_comment'].on('change', function (e) {
        // Update original form input when text typed in CKEDITOR
        e.sender.updateElement();

        // Disable submit button if required inputs are not provided.
        var checked = $('div.org-email-form').find('input:checked');
        var body_text = $.trim($("#id_comment").val());
        var subject_text = $.trim($("#id_subject").val());
        if ((checked.length == 0) || body_text == '' || subject_text == '') {
            $('input[name="submit_mail"]').prop('disabled', true);
        }
        else {
            $('input[name="submit_mail"]').prop('disabled', false);
        }
    });

    editor.fire('change');

    // allowed keys: numbers, +, -, (, ), whitespace, comma
    function phone_validate(e) {
        var theEvent = e || window.event;
        var key = theEvent.keyCode || theEvent.which;
        key = String.fromCharCode(key);
        var regex = /[0-9]|\+|\-|\(|\)|\s|\,/;
        if( !regex.test(key) ) {
            theEvent.returnValue = false;
            if(theEvent.preventDefault) theEvent.preventDefault();
        }
    }

    $('#id_phone, #id_org-phone').keypress(function(e) {
        phone_validate(e);
    });
});
