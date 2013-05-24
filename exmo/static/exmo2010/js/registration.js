// This file is part of EXMO2010 software.
// Copyright 2010, 2011 Al Nikolov
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

$(document).ready(function () {
    if ($("#id_status").val() == '1') {
        $("#id_err_position").hide();
        $("#id_position").val("");
        $("#id_row_position").hide();
        $("#id_err_phone").hide();
        $("#id_phone").val("");
        $("#id_row_phone").hide();
        $("#id_err_invitation_code").hide();
        $("#id_invitation_code").val("");
        $("#id_row_invitation_code").hide();
    }

    $('#id_status').change(function () {
        if ($("#id_status").val() == '0') {
            $("#id_row_position").show();
            $("#id_row_phone").show();
            $("#id_row_invitation_code").show();
        }
        else {
            $("#id_err_position").hide();
            $("#id_position").val("");
            $("#id_row_position").hide();
            $("#id_err_phone").hide();
            $("#id_phone").val("");
            $("#id_row_phone").hide();
            $("#id_err_invitation_code").hide();
            $("#id_invitation_code").val("");
            $("#id_row_invitation_code").hide();
        }
    });

    function helptextHandlerA( e ) {
        var top = $(e.target).position().top - 8;
        $('#help-text').show().css('top', top);
        $('.alert-info').hide();
        if ($("#id_status").val() == "0") {
            $(e.data.o).show();
        }
        else {
            $(e.data.p).show();
        }
    }

    function helptextHandlerB( e ) {
        var top = $(e.target).position().top - 8;
        $('#help-text').show().css('top', top);
        $('.alert-info').hide();
        $(e.data.p).show();
    }

    $("#id_first_name").focusin({p: '#help-name', o: '#help-name-org'}, helptextHandlerA);
    $("#id_patronymic").focusin({p: '#help-name', o: '#help-name-org'}, helptextHandlerA);
    $("#id_last_name").focusin({p: '#help-name', o: '#help-name-org'}, helptextHandlerA);
    $("#id_position").focusin({p: '#help-status'}, helptextHandlerB);
    $("#id_phone").focusin({p: '#help-phone'}, helptextHandlerB);
    $("#id_email").focusin({p: '#help-email'}, helptextHandlerB);
    $("#id_password").focusin({p: '#help-password'}, helptextHandlerB);
    $("#id_invitation_code").focusin({p: '#help-code'}, helptextHandlerB);

    $("input[type='text']").focusout(function(){
        $('#help-text').hide();
    });

    document.getElementById('id_first_name').focus();


});