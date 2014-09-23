// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
// Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
// Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
// Copyright 2014 IRSI LTD
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
$(document).ready(function () {
    // calendar initializing with user locale settings
    var settings = $.datepicker.regional[$('html').attr('lang')];
    settings['buttonImage'] = "/static/exmo2010/img/calendar.png";
    settings['buttonImageOnly'] = true;
    settings['showOn'] = "button";
    settings['changeMonth'] = true;
    settings['changeYear'] = true;
    $('.datepicker input').datepicker(settings);


    // hide interact and finishing dates if 'no_interact' checkbox is checked
    $("input[name='no_interact']").change(function() {
        $("#id_interact_date").closest("div.table-row").toggle();
        $("#id_finishing_date").closest("div.table-row").toggle();
    });

    //onload trigger for 'no_interact' checkbox
    $("input[name='no_interact']:checked").change();

    // NOTE: set interact and finishing dates to pass form validation
    // (maybe later implement proper custom validation in form)
    $("#main_form").submit(function() {
        if ($("input[name='no_interact']").is(":checked")) {
            var rate_date = $('#id_rate_date').val();
            $("#id_interact_date").val(rate_date);
            $("#id_finishing_date").val(rate_date);
        }
    });

    // manipulations with questionnaire
    if ($("#id_add_questionnaire").is(':checked')) {
        $("#addqa").show();
        $('#id_add_questionnaire').change(function () {
            if (!$("#id_add_questionnaire").is(':checked')) {
                if (confirm(gettext("You've chosen to delete monitoring's questionnaire. This will lead to removing all its questions and collected answers. Are you sure?"))) {
                    $("#id_add_questionnaire").prop('checked', false);
                    $("#addqa").hide();
                }
                else {
                    $("#id_add_questionnaire").prop('checked', true);
                }
            }
        });
    } else {
        $('#id_add_questionnaire').change(function() {
            $("#addqa").toggle();
        });
    }

    // 'donors' checkboxes onchange event
    $('input[name="donors"]:checkbox').change(function() {
        var all_scores = $('input[value="all_scores"]');
        var current_scores = $('input[value="current_scores"]');

        switch (this.value) {
            case 'all':
                $('input[name="donors"]:checkbox').not(this).prop('checked', this.checked);
                all_scores.prop('disabled', !this.checked);
                current_scores.prop('disabled', !this.checked);
                break;
            case 'all_scores':
                current_scores.prop('checked', this.checked);
                break;
            default:
                var activate = $('input[value="tasks"]').is(':checked:enabled') && $('input[value="parameters"]').is(':checked:enabled');
                all_scores.prop('disabled', !activate);
                current_scores.prop('disabled', !activate);
                if (!activate) {
                    all_scores.prop('checked', false);
                    current_scores.prop('checked', false);
                }
                break;
        }

        $('input[value="organizations"]').prop('disabled', true).prop('checked', true);

        var all_checked = $('input[name="donors"]:not(:eq(0))').not(':checked').length == 0;
        $('input[value="all"]').prop('checked', all_checked);
    });

    //onload trigger for 'donors' checkboxes
    $('input[name="donors"]:checkbox').change();
});
