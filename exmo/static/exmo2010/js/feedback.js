// This file is part of EXMO2010 software.
// Copyright 2015 IRSI LTD
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
    $('a.feedback_click').click(function(){
        $('#feedback_modal_window_content').css('width', '').css('height', '');
        var original_img = $(this).closest('div').find('img.scanned').get(0);
        var maxw = $(window).width() - 100;
        var maxh = $(window).height() - 100;

        if ((original_img.naturalWidth > maxw) && (original_img.naturalHeight > maxh)) {
            var ratio = original_img.naturalWidth / original_img.naturalHeight;
            var maxratio = maxw / maxh;
            if (maxratio > ratio) {
                // More width available than needed. We should pin only height to maintain ratio.
                $('#feedback_modal_window_content').height(maxh);
            }
            else {
                // More height available than needed. We should pin only width to maintain ratio.
                $('#feedback_modal_window_content').width(maxw);
            }
        }
        else if (original_img.naturalHeight > maxh) {
            $('#feedback_modal_window_content').width(maxw);
        }
        else if (original_img.naturalHeight > maxh) {
            $('#feedback_modal_window_content').height(maxh);
        }

        $('#feedback_modal_window_content').html($(original_img).clone().show());
        $('#feedback_modal_window').modal({overlayClose: true});
        return false;
    })
});
