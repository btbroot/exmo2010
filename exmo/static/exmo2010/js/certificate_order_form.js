// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
// Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
// Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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

    /* placeholder */
    jQuery('input[placeholder]').placeholder();

    /* Sortable table */

    $("#rating-data").tablesorter({sortList: [[0, 1]]});

    // remove verbose date before table initialization
    var v = $('td.published span.verbose').remove();

    $("#ratings-data").tablesorter({sortList: [[2, 1]], dateFormat: "ddmmyyyy"});

    // replace machine readable date with verbose one
    $('td.published span.machine').each(function(i) {
        $(this).replaceWith(v[i]);
    });

    // checked first radio button
    if(!$("input[name='task_id']").is(':checked')) {
        $("input:radio[name='task_id']:first").attr('checked', true);
    }


    $("input[name='addressee']").change(function(){
        $('.error').hide();
        if ($(this).val() == "org")
            $('.person_group').hide();
        else
            $('.person_group').show();
    });
    $("input[name='addressee']:checked").change()

    $("input[name='delivery_method']").change(function(){
        $('.error').hide();
        if ($(this).val() == "email") {
            $('.post_group').hide();
            $('.email_group').show();
        }
        else {
            $('.post_group').show();
            $('.email_group').hide();
        }
    });
    $("input[name='delivery_method']:checked").change()

    $('#id_zip_code').keypress(function(e) {
        if (e.which && (e.which < 48 || e.which > 57) && e.which != 8) {
            e.preventDefault();
        }
    });

    $('#confirm').click(function() {
        $('#certificate_form').append($('<input>', {type:'hidden', name:'confirm'}));
        $('#certificate_form').submit()
        return false;
    })

    $('#previous_form').click(function() {
        $('#certificate_form').append($('<input>', {type:'hidden', name:'back'}));
        $('#certificate_form').submit()
        return false;
    })
});
