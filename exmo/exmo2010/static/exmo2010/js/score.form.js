// This file is part of EXMO2010 software.
// Copyright 2010, 2011 Al Nikolovinpu
// Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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

jQuery.expr[':'].regex = function(elem, index, match) {
    var matchParams = match[3].split(','),
        validLabels = /^(data|css):/,
        attr = {
            method: matchParams[0].match(validLabels) ?
                matchParams[0].split(':')[0] : 'attr',
            property: matchParams.shift().replace(validLabels,'')
        },
        regexFlags = 'ig',
        regex = new RegExp(matchParams.join('').replace(/^\s+|\s+$/g,''), regexFlags);
    return regex.test(jQuery(elem)[attr.method](attr.property));
}

$(document).ready(function(){
    var $foundDash = $("#id_score-found_0"),
        $foundZero = $("#id_score-found_1"),
        $foundOne = $("#id_score-found_2"),
        $radiosDashes = $("input:not(#id_score-found_0):regex(id, id_score-.+_0)"),
        $radiosExceptFound = $("input[type='radio']:not(#id_score-found_0):not(#id_score-found_1):not(#id_score-found_2)");

    function setScoreValues(){
        var foundDashChecked = $foundDash.prop("checked"),
            foundZeroChecked = $foundZero.prop("checked");

        if (foundDashChecked || foundZeroChecked) {
            $radiosDashes.prop("checked", true);
            $radiosExceptFound.attr('disabled', true);
        } else {
            $radiosExceptFound.attr('disabled', false);
        }
    }

    var $radiosFound = $foundDash.add($foundZero).add($foundOne);

    $radiosFound.change(setScoreValues);
    setScoreValues();
});