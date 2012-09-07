// This file is part of EXMO2010 software.
// Copyright 2010, 2011 Al Nikolov
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

var qtypes = ['Текст', 'Число', 'Один из списка'];

var qaltinp = "<div class='qalt'><br /><input type='text' class='qalt'></div>";

//Обработчик клика на кнопку "Удалить".
$(".dquestion").live('click', function () {
    $(this).parent("div.qs").remove();
});

//Обработчик клика на кнопку "Изменить".
$(".rquestion").live('click', function () {
    var qdiv = $(this).parent("div.qs");
    var qquestion = qdiv.find("span.qquestion").first().text();
    var qcomment = qdiv.find("span.qcomment").first().text();
    var qtype = qdiv.find("input.qhtype").first().val();
    var qavars = $.evalJSON(qdiv.find("input.qhansvar").val());
    qdiv.html(qdc);
    qdiv.find("input.qquestion").first().val(qquestion);
    qdiv.find("input.qcomment").first().val(qcomment);
    qdiv.find("select.qtype").first().val(qtype);
    $.each(qavars, function (i) {
        qdiv.find("select.qtype").first().after(qaltinp);
        qdiv.find("input.qalt:first").val(qavars[i]);
    });
});

//Обработчик клика на кнопку "Готово".
$(".fquestion").live('click', function () {
    var qdiv = $(this).parent("div.qs");
    var qquestion = qdiv.find("input.qquestion").first().val();
    var qcomment = qdiv.find("input.qcomment").first().val();
    var qtype = qdiv.find("select.qtype").first().val();
    var qtype_str = qtypes[qtype];
    if (qquestion) {
        var qavars = [];
        if (qtype == '2') {
            qdiv.find("input.qalt").each(function (i) {
                if ($(this).val()) {
                    qavars.push($(this).val());
                }
            });
            qavars.reverse();
        }
        if ((qtype == '2' && qavars.length > 1) || qtype != '2') {
            qdiv.html(qdc2);
            qdiv.find("span.qquestion").first().text(qquestion);
            qdiv.find("span.qcomment").first().text(qcomment);
            qdiv.find("span.qtype").first().text(qtype_str);
            qdiv.find("input.qhtype").first().val(qtype);
            qdiv.find("input.qhansvar").first().val($.toJSON(qavars));
            $.each(qavars, function (i) {
                qdiv.find("span.qtype").first().after("<br /><small>" + (qavars.length - i) + ". " + qavars[i] + "</small>");
            });
            $("#addq").show();
        }
        else {
            alert("Должно быть введено не менее двух вариантов ответа!");
        }
    }
    else {
        alert("Не введен текст вопроса!");
    }
});

//Обработчик смены выбранного типа вопроса.
$("select.qtype").live('change', function () {
    var qdiv = $(this).parents("div.qs");
    if ($(this).val() == '2') {
        $(this).after(qaltinp);
        $(this).after(qaltinp);
    }
    else {
        qdiv.find("div.qalt").remove();
    }
});

//Обработчик клика по полю с вариантом ответа.
$("input.qalt").live("click", function () {
    var qdiv = $(this).parents("div.qs");
    var last_qalt = qdiv.find("input.qalt:last");
    if ($(this).is(last_qalt))
        $(this).after(qaltinp);
});

//Обработчик перехода по Tab на поле с вариантом ответа.
$("input.qalt").live("focus", function () {
    var qdiv = $(this).parents("div.qs");
    var last_qalt = qdiv.find("input.qalt:last");
    if ($(this).is(last_qalt))
        $(this).after(qaltinp);
});

//Получаем контент div'а с полями для ввода параметров вопроса.
var qdc;
$.ajax({
    url:"/exmo2010/get_qq/",
    async:false
}).done(function (data) {
            qdc = data;
        });

//Получаем контент div'а без полей для показа параметров вопроса.
var qdc2;
$.ajax({
    url:"/exmo2010/get_qqt/",
    async:false
}).done(function (data) {
            qdc2 = data;
        });

//То, что выполняется уже после загрузки документа.
$(function () {
    //Показываем форму создания вопроса при загрузке чистой страницы.
    $("#ainfo").after("<div style='background-color:#FFFFCC' class='qs'>" + qdc + "</div>");
    $("#addq").hide();


    //Обработчик клика на кнопку "Добавить вопрос".
    $("#addq").click(function () {
        if ($("div.qs").length) {
            $("div.qs:last").after("<div style='background-color:#FFFFCC' class='qs'>" + qdc + "</div>");
        }
        else{
            $("#ainfo").after("<div style='background-color:#FFFFCC' class='qs'>" + qdc + "</div>");
        }
        $("#addq").hide();
    });

    //Обработчик клика на кнопку "Сохранить анкету".
    $("#sendqq").click(function () {
        if (!$("#aname").val()) {
            alert("Не заполнено имя анкеты!");
        }
        else {
            var rez = [$("#aname").val(), $("#acomm").val(), []];
            $("div.qs").each(function (i) {
                if ($(this).find("span.qquestion").first().text()) {
                    var record = [$(this).find("span.qquestion").first().text(), $(this).find("span.qcomment").first().text(), $(this).find("input.qhtype").first().val(), []];
                    var qavars = $.evalJSON($(this).find("input.qhansvar").val());
                    $.each(qavars, function (i) {
                        record[3].push(qavars[i])
                    });
                    rez[2].push(record);
                }
            });
            if (rez[2].length == 0) {
                alert("Не создано ни одного вопроса!");
            }
            else {
                $.ajax({
                    url:"",
                    type:"POST",
                    async:false,
                    dataType:"text",
                    data:{questionaire:$.toJSON(rez)}
                }).done(function (data) {
                            $("#rform").submit();
                        });
            }
        }
    });
});
