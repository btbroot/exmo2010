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


jQuery(document).ready(function() {
    var $item = $('#header ul#navigation-menu .menu-item ul').parent('li')
        , $dropdowns = $('#header ul#navigation-menu .menu-item ul');

    $item.mouseover(function( e ){
        $(this).children('a').addClass('menuitem-hover');
        $(this).children('a').children('span').addClass('menuarrow-hover');
        e.preventDefault();
        e.stopPropagation();
    });

    $item.mouseout(function( e ){
        $(this).children('a').removeClass('menuitem-hover');
        $(this).children('a').children('span').removeClass('menuarrow-hover');
        e.preventDefault();
        e.stopPropagation();
    });

    $dropdowns.mouseout(function( e ){
        $(this).siblings('a').removeClass('menuitem-hover');
        $(this).siblings('a').children('span').removeClass('menuarrow-hover');
        e.preventDefault();
        e.stopPropagation();
    });

    var $person = $('#header ul#navigation-menu .menu-item.person > a'),
        $icon = $person.children('span'),
        $userarea = $person.siblings('#userarea');

        $person.toggle(
            function ( e ) {
                $person.addClass('menuitem-hover');
                $icon.addClass('menuarrow-hover');
                $userarea.show();
                e.preventDefault();
                e.stopPropagation();
            },
            function ( e ) {
                $person.removeClass('menuitem-hover');
                $icon.removeClass('menuarrow-hover');
                $userarea.hide();
                e.preventDefault();
                e.stopPropagation();
            }
        );
});