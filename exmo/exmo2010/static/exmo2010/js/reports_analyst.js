// This file is part of EXMO2010 software.
// Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
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
    var $headingClosed = $('td.report-title.closed'),
        $headingOpen = $('td.report-title.open'),
        $closed = $('.report-list-table.closed tbody'),
        $open = $('.report-list-table.open tbody'),
        url = $headingClosed.attr("rel"),
        $indicator = $headingClosed.children('img'),
        init = false;

    $closed.hide();
    $indicator.hide();

    $headingClosed.css('cursor','pointer');
    $headingOpen.css('cursor','pointer');

    $headingClosed.click(function() {
        if(!init) {
            $indicator.show();
            $closed.show();

            $.get(url, function( data ) {
                $indicator.hide();
                $closed.append(data);
                var $count = $("table.report-list-table.closed td.count"),
                    count = parseInt($count.html()),
                    $title = $('td.report-title.closed'),
                    txt = $title.html();
                $title.html(txt+"("+count+")");
                init = true;
            },'html');

        } else {
            $closed.toggle();
        }
    });

    $headingOpen.click(function() {
        $open.toggle();
    });
});