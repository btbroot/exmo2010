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
    // help text windows handler
    function helptextHandler( e ) {
        var top = $(e.target).position().top;
        var left = $(e.target).position().left + $(e.target).width();
        $('.help-text').css('top', top).css('left', left).show();
        $('.info-block').hide();
        $(e.data.p).show();
    }

    $("#id_email").focusin({p: '#help-emails'}, helptextHandler);
    $("#id_phone").focusin({p: '#help-phones'}, helptextHandler);
    $("textarea").focusout(function(){$('.help-text').hide();});

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

    $('#id_phone').keypress(function(e) {
        phone_validate(e);
    });
});
