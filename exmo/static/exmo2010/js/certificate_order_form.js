// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
// Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
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
    var $person_group = $('.person_group');
    var $post_group = $('.post_group');
    var $email_group = $('.email_group');

    var $radio_certificate_for = $("input[name='0-certificate_for']:checked");
    var $radio_delivery_method = $("input[name='0-delivery_method']:checked");

    /* placeholder */
    jQuery('input[placeholder]').placeholder();

    /* Sortable table */

    var dateFormat = "ddmmyyyy";

    $("#rating-data").tablesorter({sortList: [[0, 1]]});

    // remove verbose date before table initialization
    var v = $('td.published span.verbose').remove();

    $("#ratings-data").tablesorter({sortList: [[2, 1]], dateFormat: dateFormat});

    // replace machine readable date with verbose one
    $('td.published span.machine').each(function(i) {
        $(this).replaceWith(v[i]);
    });

    // checked first radio button
    if(!$("input[name='0-task_id']").is(':checked')) {
        $("input:radio[name='0-task_id']:first").attr('checked', true);
    }

    function certificate_for_group(e) {
        switch (e.val()) {
            case "0":
                $person_group.hide();
                break;
            case "1":
                $person_group.show();
                break;
        }
    }

    function delivery_method_group(e) {
        switch (e.val()) {
            case "0":
                $post_group.hide();
                $email_group.show();
                break;
            case "1":
                $post_group.show();
                $email_group.hide();
                break;
        }
    }

    $("input[name='0-certificate_for']").change(function() {
        $('.error').hide();
        certificate_for_group($(this));
    });

    $("input[name='0-delivery_method']").change(function(){
        $('.error').hide();
        delivery_method_group($(this));
    });

    certificate_for_group($radio_certificate_for);
    delivery_method_group($radio_delivery_method);

    $('#id_0-zip_code').keypress(function(e) {
        if (e.which && (e.which < 48 || e.which > 57) && e.which != 8) {
            e.preventDefault();
        }
    });

    function is_email(email) {
        var regex  = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        return regex.test(email);
    }

    function insert_required_error_before(element, id) {
        var $error_block = '<p class="error warning">' + $('label[for=' + id + ']').text() + ' ' + gettext('is required field.') + '</p>';
        $($error_block).insertBefore(element);
    }


    $("#certificate_form").submit(function() {
        var $error_block;
        var $no_errors = true;
        var $name = $('#id_0-name');
        var $wishes = $('#id_0-wishes');
        var $email = $('#id_0-email');
        var $for_whom = $('#id_0-for_whom');
        var $zip_code = $('#id_0-zip_code');
        var $address = $('#id_0-address');

        var $certificate_for_value = $("input[name='0-certificate_for']:checked").val();
        var $delivery_method_value = $("input[name='0-delivery_method']:checked").val();

        $('.error').remove();

        switch ($certificate_for_value) {
            // certificate for organization
            case "0":
                break;
            // certificate for person
            case "1":
                if (!$name.val()) {
                    insert_required_error_before('div.person_group', $name.attr('id'));
                    $no_errors = false;
                }
                break;
        }

        switch ($delivery_method_value) {
            // send by email
            case "0":
                if (!$email.val()) {
                    insert_required_error_before('div.email_group', $email.attr('id'));
                    $no_errors = false;
                } else if (!is_email($email.val())) {
                    $error_block = '<p class="error warning">' + gettext('Enter correct email.') + '</p>';
                    $($error_block).insertBefore('div.email_group');
                    $no_errors = false
                }
                break;
            // send by post
            case "1":
                if (!$for_whom.val()) {
                    insert_required_error_before('div.post_group', $for_whom.attr('id'));
                    $no_errors = false;
                } else if (!$zip_code.val()) {
                    insert_required_error_before('div.post_group', $zip_code.attr('id'));
                    $no_errors = false;
                } else if ($zip_code.val() && $zip_code.val().length < 6) {
                    $error_block = '<p class="error warning">' + gettext('Enter correct zip code.') + '</p>';
                    $($error_block).insertBefore('div.post_group');
                    $no_errors = false;
                } else if (!$address.val()) {
                    insert_required_error_before('div.post_group', $address.attr('id'));
                    $no_errors = false;
                }
                break;
        }

        if ($no_errors) {
            switch ($certificate_for_value) {
                // certificate for organization
                case "0":
                    $name.prop('disabled', true);
                    $wishes.prop('disabled', true);
                    break;
                // certificate for person
                case "1":
                    break;
            }

            switch ($delivery_method_value) {
                // send by email
                case "0":
                    $for_whom.prop('disabled', true);
                    $zip_code.prop('disabled', true);
                    $address.prop('disabled', true);
                    break;
                // send by post
                case "1":
                    $email.prop('disabled', true);
                    break;
            }

        }

        return $no_errors;
    });

});
