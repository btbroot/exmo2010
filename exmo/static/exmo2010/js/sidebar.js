// This file is part of EXMO2010 software.
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

$(function(){
    // Highlight currently active tab in the sidebar.
    var requested_urlname = $('#sidebar').data('urlname');
    $('#sidebar li').each(function(){
        var urls = $(this).data('urls');
        if (urls == undefined) {
            return;
        }
        if(urls.split(' ').indexOf(requested_urlname) >= 0) {
            // Mark item as selected.
            $(this).addClass('selected');
            // Replace link with text to prevent clicking it again.
            $(this).find('a').replaceWith($(this).text());
        }
    });

    $(window).resize(function() {
        // sidebar_pad.top = sidebar.bottom
        $("#sidebar_pad").css({top: $('#sidebar').offset().top + $('#sidebar').height()});
    });

    $("#sidebar_pad").show();

    $(window).resize();
});
