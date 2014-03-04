// This file is part of EXMO2010 software.
// Copyright 2013 Al Nikolov
// Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
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
    var $comments = $('#comments').length;

    // TICKET 1516: inactive CKEditor
    function redraw_ckeditor_width(editor) {
        $('#cke_contents_' + editor).children()[1].style.width = '100%';
    }

    // tabs clicking (comment, clarification, claim)
    $('.ccc-tabs').live('click', function(e) {
        var $link, editor;

        switch (e.target.hash) {
           case '#comments':
              $tab_content_clarifications.hide();
              $tab_content_claims.hide();
              $tab_content_comments.show();
              editor = 'id_comment';
              break;
           case '#clarifications':
              $tab_content_comments.hide();
              $tab_content_claims.hide();
              $tab_content_clarifications.show();
              editor = 'id_clarification-comment';
              break;
           case '#claims':
              $tab_content_comments.hide();
              $tab_content_clarifications.hide();
              $tab_content_claims.show();
              editor = 'id_claim-comment';
              break;
        }
        redraw_ckeditor_width(editor);
        $link = $('a[href="' + e.target.hash + '"]');
        $link.parent().addClass('active').siblings().removeClass('active');
        window.location.hash = '';

        return false;
    });

    // only for form page without comments (clarification tab by default)
    if ($comments == 0) {
        $('a[href="#clarifications"]').click();
    }
    $hash && $('a[href="' + $hash + '"]').click();
});
