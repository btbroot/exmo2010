// This file is part of EXMO2010 software.
// Copyright 2013 Foundation "Institute for Information Freedom Development"
// Copyright 2013 Al Nikolov
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
    // GIVEN parameters form
    var $submit = $('#pselect_form > input[type="submit"]'),
        $checkboxes = $('#pselect_form > div >input[type="checkbox"]');

    module("rating", {
        setup: function() {

        },

        teardown: function() {
            $checkboxes.each(function(){
                $(this).prop("checked", false);
            });
        }
    });

    // WHEN user gets the form
    test("Checkboxes unchecked and submit disabled", function() {
        // THEN all checkboxes unchecked
        $checkboxes.each(function(){
            equal($(this).prop("checked"), false);
        });
        // AND submit button is disabled
        equal($submit.prop("disabled"), true);
    });

    // WHEN user gets the form
    test("Checkbox checked and submit enabled", function() {
        // AND clicks one item
        $checkboxes.first().trigger( "click" );
        $checkboxes.first().triggerHandler( "click" );
        // THEN item is checked
        equal($checkboxes.first().prop("checked"), true);
        // AND submit button is enabled
        equal($submit.prop("disabled"), false);
    });
})