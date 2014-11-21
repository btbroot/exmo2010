// This file is part of EXMO2010 software.
// Copyright 2010, 2011 Al Nikolov
// Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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

$(document).ready(function () {
    // if JS is available show login/registration/password recovery form
    // else 'noscript' tag will show warning message
    $('.auth-content-block').show();
    $('h1').show();

    if($('.auth-content-block form').hasClass('registration-form')) {
        var all_text_inputs = $('input[type="text"]');

        // show info block of focused input element
        all_text_inputs.focusin(function() {
            $(this).closest('.table-row').find('.info-block').show();
        });

        // hide all info blocks
        all_text_inputs.focusout(function(){
            $('.info-block').hide();
        });
    }

    // set focus on email field by default
    $('input[name="email"]').focus();
});
