// This file is part of EXMO2010 software.
// Copyright 2014 Foundation "Institute for Information Freedom Development"
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

// Make sidebar column 100% in height
function columnHeight() {
    // Sidebar height should equal the document height minus the header height,
    // breadcrumbs height, sidebar title height and footer height
    var newHeight = $(document).height() - ($("#header").height() + $(".breadcrumbs").outerHeight()
        + $('h1').outerHeight() + $("#footer").height()) + "px";
    $("#nav-sidebar").css("height", newHeight);
}

// On page load
$(window).load(columnHeight);

// On window resize
$(window).resize( function () {
    // Clear forced sidebar height before recalculating after window resize
    $("#nav-sidebar").css("height", "");
    columnHeight();
});
