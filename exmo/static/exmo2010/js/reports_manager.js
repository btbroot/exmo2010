// This file is part of EXMO2010 software.
// Copyright 2010, 2011 Al Nikolov
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

$(document).ready(function () {
    $('#id_addressee').change(function () {
        $('#cform').submit();
    });
    $('#id_creator').change(function () {
        $('#cform').submit();
    });
    var $titleOpen = $('.title.open span'),
        $titleClosed = $('.title.closed span'),
        $tableOpen = $('table.messages-report.open'),
        $tableClosed = $('table.messages-report.closed');

    $tableClosed.hide();
    $titleOpen.css('cursor', 'pointer');
    $titleClosed.css('cursor', 'pointer');

    $tableOpen.hide();
    $('td.addressee').width($('th.addressee').width());
    $('td.creator').width($('th.creator').width());
    $tableOpen.show();

    $titleOpen.click(function() {
        $tableOpen.toggle();
    });

    var init = false;
    var $indicator = $titleClosed.siblings('img');

    $indicator.hide();

    var creator_id = parseInt($("#id_creator option:selected").val()),
        addressee_id = parseInt($("#id_addressee option:selected").val()),
        url = $titleClosed.parents("td").attr("rel"),
        $closed = $(".messages-report.closed");

    $titleClosed.click(function( e ) {
        if (!init) {
            $indicator.show();

            $.get(url, { creator_id: creator_id, addressee_id: addressee_id }, function( data ) {
                $indicator.hide();
                $closed.append(data);
                var $count = $(".messages-report.closed td.count"),
                    count = parseInt($count.html());

                if (!isNaN(count)) {
                    $titleClosed.closest("td").append("("+count+")");
                } else {
                   $('.empty').show();
                }

                $('td.addressee').width($('th.addressee').width());
                $('td.creator').width($('th.creator').width());

                $closed.show();
                init = true;
            }, 'html');
        } else {
            $closed.toggle();
        }

        e.stopPropagation();
        e.preventDefault();
    });

});
