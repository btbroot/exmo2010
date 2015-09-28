// This file is part of EXMO2010 software.
// Copyright 2014-2015 IRSI LTD
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
    $('input[placeholder], textarea[placeholder]').placeholder();
    $(".base-table").tablesorter({sortList: [[1, 0]], headers: {0: {sorter: false}}});


    $(".modal a.close_window").click(function() {
        $.modal.close();
        return false;
    });


    // Clicking 'select all' checkbox should toggle all checkboxes.
    $('input[type="checkbox"].group_actions.toggle_all').click(function(){
        if ($(this).prop('checked')){
            $('input[type="checkbox"].group_actions').prop('checked', true);
        }
        else {
            $('input[type="checkbox"].group_actions').prop('checked', false);
        }
    })

    // Disable group action button if no checkbox is checked.
    var group_action_checkup = function() {
        if ($('input[type="checkbox"].group_actions:checked').length > 0) {
            $('#group_actions input.action').prop('disabled', false);
        }
        else {
            $('#group_actions input.action').prop('disabled', true);
        }
    }

    // Perform group action checkup on page load.
    group_action_checkup();

    // Perform group action checkup when checkbox clicked.
    $('input[type="checkbox"].group_actions').click(group_action_checkup);


    // Go to send_mail page with selected orgs when send_mail group action button clicked.
    $('#group_actions input.send_mail').click(function(){
        var checked = $('input[type="checkbox"].group_actions:checked').not('.toggle_all');

        var pks = [];
        for (var i=0; i<checked.length; i++) {
            pks.push( $(checked[i]).closest('tr').data('pk'))
        }
        url = $('#group_actions').data('sendmail_url') + '?' + $.param({orgs: pks}, true);
        window.location = url;
    })

    // Show invite_links modal window when create_inv_links group action button clicked.
    $('#group_actions input.create_inv_links').click(function(){
        var checked = $('input[type="checkbox"].group_actions:checked').not('.toggle_all');
        if (checked.length == 1) {
            // Only one organization selected.
            show_single_org_modal(checked.closest('tr').data())
        } else {
            // More than one organization selected.
            $('.single_org_digest').hide();
            $('.multi_org_digest').show();

            var codes = [];
            var names = [];
            for (var i=0; i<checked.length; i++) {
                var org_data = $(checked[i]).closest('tr').data();
                codes.push(org_data.code)
                names.push(org_data.name)
            }

            // Show digest of all organization names. (max of 3)
            if (names.length <= 3) {
                var digest = names.join('<br/>');
            } else {
                var digest = names.slice(0, 3).join('<br/>');
                var _andmore = gettext('and %(num_not_shown_orgs)s more');
                digest += '<br/>' + interpolate(_andmore, {num_not_shown_orgs: names.length - 3}, true);
            }
            $('#invite_links_window td.names').html(digest);

            // Store invite codes of all currently selected orgs.
            $('#invite_links_window').data('inv_codes', codes.join(','));

            // Delete existing widgets, except prototype.
            $('.invite_widgets tr').not('.hidden').remove();

            // Create one new widget with empty email.
            add_inv_widget();

            // Show modal window.
            $('#invite_links_window').modal({overlayClose: true});
        }
        return false;
    })

    var show_single_org_modal = function(org_data){
        $('.single_org_digest').show();
        $('.multi_org_digest').hide();

        // Store invite code of selected org.
        $('#invite_links_window').data('inv_codes', org_data.code)

        // Delete existing widgets, except prototype.
        $('.invite_widgets tr').not('.hidden').remove();

        // Create invite widgets for every email of this organization.
        var emails = org_data.email.split(', ');
        for (var i=0; i<emails.length; i++) {
            if (emails[i].trim().length > 0) {
                add_inv_widget(emails[i]);
            }
        }

        // Create one new widget with empty email.
        add_inv_widget();

        // Show org name in modal window.
        $('#invite_links_window td.name').html(org_data.name);

        // Show modal window.
        $('#invite_links_window').modal({overlayClose: true});
    }

    $('a.org_invite_link').click(function(){
        show_single_org_modal($(this).closest('tr').data())
        return false;
    })

    var generate_invite_link = function(tr_widget) {
        var data = $('#invite_links_window').data()
        var query = {code: data.inv_codes.split(',')}
        var email = tr_widget.find('input.email').val().trim();
        if (email != '') {
            query.email = email;
        }
        tr_widget.find('input.invite_link').val(data.baselink + '?' + $.param(query, true))
    }

    // Regenerate invite_link when email input is changed.
    $('.invite_widgets').on('keyup', 'input.email', function(){
        generate_invite_link($(this).closest('tr'))
    })

    var add_inv_widget = function(email) {
        var tr_widget = $('.invite_widgets tr.hidden').clone().removeClass('hidden');
        if (email != undefined) {
            tr_widget.find('input.email').val(email.trim());
        }
        generate_invite_link(tr_widget);
        tr_widget.appendTo('.invite_widgets');
    }

    // Add new invite widget when last widget's email input become filled and loses focus.
    $('.invite_widgets').on('focusout', 'input.email:last', function(){
        if ($(this).val().trim() != '') {
            add_inv_widget()
        }
    })

    // On click select all invite_link text inside input.
    $('.invite_widgets').on('click', 'input.invite_link', function(){ this.select(); });

    // Forbid manual editing invite_link input.
    $('.invite_widgets').on('keypress', 'input.invite_link', function(e){
        if (e.key == 'c' && (e.ctrlKey == true || e.metaKey == true)) {
            return true;  // allow to copy text
        }
        return false;
    })

});
