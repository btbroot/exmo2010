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
//

$(function(){
    // Try to restore hidden state from cookies.
    if (readCookie('hide_login_bubble') != null) {
        $('#login_bubble').hide();
    }

    $('body').on('click', '#login_bubble .close', function(){
        // Store hidden state in cookies.
        createCookie('hide_login_bubble', 'yeah!', 30)

        $('#login_bubble').hide();
        return false;
    })
});
