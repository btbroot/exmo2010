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

$(document).ready(function() {
    /* placeholder */
    jQuery('input[placeholder]').placeholder();

    /* Sortable table */

    var thClasses = new Array(5),
    dateFormat = "ddmmyyyy"

    function modalOpenHandler() {
        $('#rating-data th').each(function(i) {
            thClasses[i] = ($(this).attr('class'));
        });
    }

    function modalCloseHandler() {
        $('#rating-data th').each(function(i) {
             $(this).attr('class', thClasses[i]);
        });
        $.modal.close();
    }

    $("#rating-data").tablesorter({sortList: [[0,0]]});

    // remove verbose date before table initialization
    var v = $('td.published span.verbose').remove()

    $("#ratings-data").tablesorter({sortList: [[2,1]], dateFormat: dateFormat});

    // replace machine readable date with verbose one
    $('td.published span.machine').each(function(i) {
        $(this).replaceWith(v[i]);
    })

    /* Modal */

    $(document).on('mousewheel', '.simplemodal-overlay, .simplemodal-data', function() {
        return false;
    });

    $("#modal-open").click(function( e ) {
        modalOpenHandler();

        $("#settings-modal").modal({
            overlayClose: true,
            onClose: modalCloseHandler
        });

        e.preventDefault();
    });

    $("#cancel-link").click(function( e ) {
        $.modal.close();
        e.preventDefault();
    });

    /* User defined menu item */

    $('#user-defined').click(function( e ) {
        $('.switcher > li > a').each(function() {
            $(this).parent().removeClass('active');
            $(this).removeClass('off');
        });

        $(this).addClass('off');
        $(this).parent().addClass('active');

        $("#user-defined-parameters").removeClass('hidden');

        e.preventDefault();
    });

    /* Toggle parameters */

    function parametersToggle() {
        if(!$('#pselect_form').is(":visible")) {
            $('#user-defined-parameters>p a').html(gettext('hide'));
            $('#user-defined-parameters>form').removeClass('hidden');

        } else {
            $('#user-defined-parameters>p a').html(gettext('show'));
            $('#user-defined-parameters>form').addClass('hidden');

        }
    }

    $('#user-defined-parameters>p a').click(function( e ) {
        parametersToggle();
        e.preventDefault();
    })

    /* User defined mode, submit button ability */

    var $submit = $('#pselect_form > input[type="submit"]'),
        $checkboxes = $('#pselect_form > div input[type="checkbox"]');

    function isAnyChecked() {
        var any_checked = false
        $checkboxes.each(function() {
            var checked = $(this).attr('checked');
            if (checked)
                any_checked = true;
        });
        return any_checked;
    }

    function setSubmitButtonAbility() {
        if ( isAnyChecked() )
            $submit.attr("disabled", false);
        else
            $submit.attr("disabled", true);
    }

    setSubmitButtonAbility();

    $checkboxes.click(function() {
        setSubmitButtonAbility();
    });
});
