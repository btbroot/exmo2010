// This file is part of EXMO2010 software.
// Copyright 2013 Al Nikolov
// Copyright 2013 Foundation "Institute for Information Freedom Development"
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
    var $hash = window.location.hash;
    var $tab_content_comments = $('.tab-content-comments');
    var $tab_content_clarifications = $('.tab-content-clarifications');
    var $tab_content_claims = $('.tab-content-claims');

    // tabs clicking (comment, clarification, claim)
    $('.ccc-tabs').live('click', function(e) {
        var $link;

        switch (e.target.hash) {
           case '#comments':
              $tab_content_clarifications.hide();
              $tab_content_claims.hide();
              $tab_content_comments.show();
              break;
           case '#clarifications':
              $tab_content_comments.hide();
              $tab_content_claims.hide();
              $tab_content_clarifications.show();
              break;
           case '#claims':
              $tab_content_comments.hide();
              $tab_content_clarifications.hide();
              $tab_content_claims.show();
              break;
        }
        $link = $('a[href="' + e.target.hash + '"]');
        $link.parent().addClass('active').siblings().removeClass('active');
        window.location.hash = '';

        return false;
    });

    $hash && $('a[href="' + $hash + '"]').click();
});
