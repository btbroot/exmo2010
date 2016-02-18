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

    // Show/hide keywords block
    $('a[href="#show_keywords"]').click(function(e){
        $(".keywords-block").slideToggle();
        e.preventDefault();
    });

    // When group checkbox clicked, toggle all children
    $("div.destination input.group").click(function () {
        $(this).closest('div.destination').find('input').prop('checked', $(this).prop('checked'));
    });

    if (CKEDITOR.env.isCompatible) {
        $('#preview_btn').prop('disabled', true);
        $('input[type="submit"]').prop('disabled', true);
        var editor = CKEDITOR.instances['id_comment'];

        $("div.destination input").click(function () {
            // When children checkbox unchecked, uncheck group checkbox too
            if ($(this).prop('checked') == false) {
                $(this).closest('div.destination').find('input.group').prop('checked', false);
            }
            // Trigger ckeditor change to handle disabling preview button.
            editor.fire('change');
        });

        $("#id_subject").on('keyup', function () {
            // Trigger ckeditor change to handle disabling preview button.
            editor.fire('change');
        });

        CKEDITOR.instances['id_comment'].on('change', function (e) {
            // Update original form input when text typed in CKEDITOR
            e.sender.updateElement();

            $('.preview-block').hide('slow');
            $('input[type="submit"]').prop('disabled', true).hide('slow');
            // Disable preview button if required inputs are not provided.
            var checked = $('div.org-email-form').find('input:checked');
            var body_text = $.trim($("#id_comment").val());
            var subject_text = $.trim($("#id_subject").val());
            var disabled = checked.length == 0 || body_text == '' || subject_text == '';
            $('#preview_btn').prop('disabled', disabled);
        });

        editor.fire('change');
    }


    $('#email_form').submit(function() {
        var inputValues = {};
        $('#attachments div').each(function() {
            inputValues[$(this).data('filename')] = $(this).text();
        });
        $('input[name="attachments_names"]').val(JSON.stringify(inputValues));
    });


    /* One-click upload attachments */

    $('#upload_link').click(function() {
        if ($('#attachments').children().length < 10) {
            $('#upload_form input[type="file"]').click();
        } else {
            alert(gettext('Too many attachments.'));
        }
        return false
    });

    function beforeSubmit(arr, $form, options) {
        $('.progressbar').show();
    }

    function onProgress(event, position, total, percentComplete) {
        //update progressbar percent complete
        $('.progressbar div').width(percentComplete + '%');
    }

    $('#upload_form').change(function () {
        var form = this;

        $(this).ajaxSubmit({
            beforeSubmit: beforeSubmit,
            uploadProgress: onProgress,
            success: function(data) {
                $('.progressbar').hide();
                if (data.error) {
                    alert(data.error)
                } else {
                    var element = $('<div data-filename="' + data["saved_filename"] + '">' +
                                    data["original_filename"] + '<a><i class="icon delete"></i></a></div>');
                    $('#attachments').append(element);
                }
                form.reset();
            },
            error: function(jqXHR, textStatus, errorMessage) {
                $('.progressbar').hide();
                alert(errorMessage);
                form.reset();
            },
            resetForm: true
        });

        return false;
    });

    $('#attachments').on('click', 'a', function(){
        $(this).closest('div').remove();
    });

    // Send ajax-request to get email preview
    $('#preview_btn').click(function() {

        $('#email_form').ajaxSubmit({
            dataType: 'json',
            success: function(data) {
                var iframe = $('#iframe_preview');
                iframe.height('auto');
                iframe.contents().find('html').html(data['page']);
                $('.preview-block').show();
                iframe.height(iframe.contents().find('html').height());
                if (!data.error) {
                    $('input[type="submit"]').prop('disabled', false).show();
                }
            },
            error: function(jqXHR, textStatus, errorMessage) {
                alert(errorMessage);
            }
        });

        return false
    });
});
