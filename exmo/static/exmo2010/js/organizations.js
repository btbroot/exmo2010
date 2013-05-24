// This file is part of EXMO2010 software.
// Copyright 2010, 2011 Al Nikolov
// Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
    $("td.comment").click(function( e ) {
        $(this).children('div.preview-container').toggle();
        $(this).children('div.full').toggle();
    });

    $(function() {
        $( ".jdatefield" ).datepicker({
            dateFormat: "dd.mm.yy",
            changeMonth: true,
            changeYear: true,
            numberOfMonths: 3,
            maxDate: "0m 0w 0d"
        });
    });

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

    return $('a[data-toggle="tab"]').on('shown', function(e) {
      return location.hash = $(e.target).attr('href').substr(1);
    });
});