// This file is part of EXMO2010 software.
// Copyright 2010, 2011, 2013 Al Nikolov
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
//
$(document).ready(function () {
    // calendar initializing
    var lang = $('html').attr('lang');
    var settings = $.datepicker.regional[ lang ];
    settings['buttonImage'] = "/static/exmo2010/img/calendar.png";
    settings['buttonImageOnly'] = true;
    settings['showOn'] = "button";
    settings['changeMonth'] = true;
    settings['changeYear'] = true;
    $( ".datepicker" ).datepicker(settings);

    if ($("#id_no_interact").is(':checked')) {
        $("#id_interact_date").closest("tr").hide();
        $("#id_finishing_date").closest("tr").hide();
    }

    $('#id_no_interact').change(function () {
        if ($("#id_no_interact").is(':checked')) {
            $("#id_interact_date").closest("tr").hide();
            $("#id_finishing_date").closest("tr").hide();
        }
        else {
            $("#id_interact_date").closest("tr").show();
            $("#id_finishing_date").closest("tr").show();
        }
    });

    $("#main_form").submit(function(e) {
        if ($("#id_no_interact").is(':checked')) {
            $("#id_interact_date").val($("#id_rate_date").val());
            $("#id_finishing_date").val($("#id_rate_date").val());
        }
    });


    if ($("#id_add_questionnaire").is(':checked')) {
        $('#id_add_questionnaire').change(function () {
            if (!$("#id_add_questionnaire").is(':checked')) {
                if (confirm(gettext("You've chosen to delete monitoring's questionnaire. This will lead to removing all its questions and collected answers. Are you sure?"))) {
                    $("#id_add_questionnaire").attr('checked', false);
                }
                else {
                    $("#id_add_questionnaire").attr('checked', true);
                }
            }
        });
    }
    else {
        $('#id_add_questionnaire').change(function () {
            if ($("#id_add_questionnaire").is(':checked')) {
                $("#addqa").show();
            }
            else {
                $("#addqa").hide();
            }
        });
    }
});
