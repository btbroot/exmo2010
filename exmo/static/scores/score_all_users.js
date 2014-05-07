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
$(document).ready(function() {
    $('a[href="#show_explanations"]').click(function(e){
        $(".explanations-block").slideToggle(function(){
            var link = $(e.target);
            if ($(this).is(":visible")) {
                link.text(gettext('hide explanations'));
            } else {
                link.text(gettext('show explanations'));
            }
        });
        e.preventDefault();
    });

    $('a[href="#show_score_rev1"]').click(function(e){
        var score_rev1 = $(".score_rev1");
        var link = $(e.target);
        var show = 1;

        if (score_rev1.is(":visible")) {
            score_rev1.addClass('hidden');
            link.text(gettext('show initial scores'));
            show = 0;
        } else {
            score_rev1.removeClass('hidden');
            link.text(gettext('hide initial scores'));
        }
        if ($(this).data("active") == 'True') {
            $.post($(this).data("url"), {show_score_rev1: show});
        }
        e.preventDefault();
    });
});
