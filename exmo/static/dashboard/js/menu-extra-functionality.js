// This file is part of EXMO2010 software.
// Copyright 2010, 2011 Al Nikolov
// Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
// Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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


jQuery(document).ready(function() {
    var $item = $('ul#navigation-menu .menu-item ul')
        .parent('li').children('a');

    var $person = $('ul#navigation-menu .menu-item.person > a'),
        $icon = $person.children('span'),
        $userArea = $person.siblings('#userarea');

    function hideDropDown ($this) {
        $this.removeClass('menuitem-hover');
        $this.children('span').removeClass('menuarrow-hover');
        $this.siblings('ul').hide();
    }

    function hideUserArea () {
        $person.removeClass('menuitem-hover');
        $icon.removeClass('menuarrow-hover');
        $userArea.hide();
    }

    $item.click(
        function ( e ) {
            if (!$(this).hasClass('menuitem-hover')) {
                $(this).addClass('menuitem-hover');
                $(this).children('span').addClass('menuarrow-hover');
                $(this).siblings('ul').show();
                hideUserArea();
            } else {
                hideDropDown($(this));
            }

            e.preventDefault();
            e.stopPropagation();
        }
    );

    $person.click(
        function ( e ) {
            if (!$person.hasClass('menuitem-hover')) {
                $person.addClass('menuitem-hover');
                $icon.addClass('menuarrow-hover');
                $userArea.show();
                hideDropDown($item);
            } else {
                hideUserArea();
            }

            e.preventDefault();
            e.stopPropagation();
        }
    );

    $('html').click(function() {
        hideDropDown($item);
        hideUserArea();
    });

    // set language forms handlers
    $('form[name="switch_lang"] a').click(function() {
        $(this).closest('form').submit();
        return false;
    });
});
