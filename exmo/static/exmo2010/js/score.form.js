// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
// Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
};

$(document).ready(function() {
    var $foundDash = $("#id_score-found_0"),
        $foundZero = $("#id_score-found_1"),
        $foundOne = $("#id_score-found_2"),
        $radiosDashes = $("input:not(#id_score-found_0):regex(id, id_score-.+_0)"),
        $radiosExceptFound = $("input[type='radio']:not(#id_score-found_0):not(#id_score-found_1):not(#id_score-found_2)"),
        $inputCommentFound = $("#id_score-foundComment"),
        $inputCommentsExceptFound = $("textarea:not(#id_score-foundComment):regex(id, id_score-.+Comment)"),
        $inputComments = $("textarea:regex(id, id_score-.+Comment)"),
        $radios = $("input[type='radio']"),
        comments = [],
        commentStatuses = [],
        radioStatuses = [];

    $('textarea:not(#id_comment):not(#id_score-comment)').autosize();

    $inputComments.each(function() {
        comments.push($(this).html());
    });

    function setScoreValues(){
        var foundDashChecked = $foundDash.prop("checked"),
            foundZeroChecked = $foundZero.prop("checked");

        if (foundDashChecked || foundZeroChecked) {
            $radiosDashes.prop("checked", true);
            $radiosExceptFound.attr('disabled', true);
            $inputCommentsExceptFound.text('');
            $inputCommentsExceptFound.val('');
            $inputCommentsExceptFound.attr('disabled', true);
        } else {
            $radiosExceptFound.attr('disabled', false);
            $inputCommentsExceptFound.attr('disabled', false);
        }

        if (foundDashChecked) {
            $inputCommentFound.text('');
            $inputCommentFound.val('');
            $inputCommentFound.attr('disabled', true);
        } else {
            $inputCommentFound.attr('disabled', false);
        }
    }

    var $radiosFound = $foundDash.add($foundZero).add($foundOne);

    $radiosFound.change(setScoreValues);
    setScoreValues();

    $inputComments.each(function() {
        commentStatuses.push($(this).is(':disabled'));
    });

    $radios.each(function() {
        radioStatuses.push($(this).is(':disabled'));
    });

    $('input[type="reset"]').click(function() {
        $inputComments.each(function( i ) {
            $(this).html(comments[i]);
            $(this).attr('disabled', commentStatuses[i]);
        });
        $radios.each(function( i ) {
            $(this).attr('disabled', radioStatuses[i]);
        });
    });

    $("form.score").submit(function() {
      $("#submit_score").prop('disabled',true);
    });

    $('.edit-tabs').live('click', function(e) {
        var $link;
        var $form_comment = $('.comment-form');

        switch (e.target.hash) {
           case '#reply':
              $link = $('a[href="#reply"]');
              $form_comment.show();
              break;
           case '#change_score':
              $link = $('a[href="#change_score"]');
              $form_comment.hide();
              break;
           case '#edit':
              $link = $('a[href="#edit"]');
              $form_comment.hide();
              break;
        }

        $link.parent().addClass('active').siblings().removeClass('active');
    })
});
