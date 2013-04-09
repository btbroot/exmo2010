# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Модуль вью для работы с мониторингами
"""

import simplejson
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseForbidden, Http404
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.translation import ugettext as _

from bread_crumbs.views import breadcrumbs
from exmo2010.models import Parameter, Questionnaire
from exmo2010.models import Monitoring, QQuestion, AnswerVariant
from exmo2010.models import QUESTION_TYPE_CHOICES


@csrf_exempt
def add_questionnaire(request, m_id):
    """
    Создание опросника анкеты мониторинга.
    Формат входящего json-файла (уже дисериализованного):
    [
     "Название анкеты",
     "Примечание к анкете",
     [
      ("Текст вопроса", "Пояснение к вопросу", 0, []),
      ("Текст вопроса2", "", 1, []),
      ("Текст вопроса3", "Пояснение к вопросу3", 2, ["Первый вариант ответа",
       "Второй вариант ответа", "Третий вариант ответа"]),
     ]
    ]
    """
    monitoring = get_object_or_404(Monitoring, pk=m_id)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    if monitoring.has_questions():
        return HttpResponseForbidden(_('Forbidden'))
    if request.method == "POST":
        if request.is_ajax():
            questionset_json = request.POST.get("questionaire")
            try:
                questionset = simplejson.loads(questionset_json)
            except simplejson.JSONDecodeError:
                questionset = None
            if questionset:
                a_name, a_comm, qlist = questionset
                questionnaire = Questionnaire.objects.get_or_create(
                    monitoring=monitoring)[0]
                questionnaire.title = a_name
                questionnaire.comment = a_comm
                questionnaire.save()
                for q in qlist:
                    q_question, q_comment, q_type, q_a_variants = q
                    new_question = QQuestion(questionnaire=questionnaire)
                    new_question.qtype = int(q_type)
                    new_question.question = q_question
                    if q_comment:
                        new_question.comment = q_comment
                    new_question.save()
                    if int(q_type) == 2:  # Выбор варианта ответа.
                        for a in q_a_variants:
                            new_answer = AnswerVariant(qquestion=new_question)
                            new_answer.answer = a
                            new_answer.save()
            return HttpResponse("Опросник создан!")
        else:
            return HttpResponseForbidden(_('Forbidden'))
    else:
        title = _('Edit monitoring %s') % monitoring
        # title0 - потому что переменную title ждет темплейт base.html и
        # использует не так, как мне тут нужно.

        crumbs = ['Home', 'Monitoring']
        breadcrumbs(request, crumbs, monitoring)
        current_title = _('Add questionnaire')

        return render_to_response('exmo2010/add_questionnaire.html',
            {"monitoring": monitoring, "current_title": current_title, "title0": title},
            context_instance=RequestContext(request))


def get_qq(request):
    """AJAX-вьюха для получения кода div'а для одного вопроса (c полями)"""
    if request.method == "GET" and request.is_ajax():
        return render_to_response('exmo2010/forms/question_div.html',
            {"choices": QUESTION_TYPE_CHOICES,},
            context_instance=RequestContext(request))
    else:
        raise Http404


def get_qqt(request):
    """AJAX-вьюха для получения кода div'а для одного вопроса (без полей)"""
    if request.method == "GET" and request.is_ajax():
        return render_to_response('exmo2010/forms/question_div2.html',
            context_instance=RequestContext(request))
    else:
        raise Http404

@csrf_exempt
def get_pc(request):
    """AJAX-вьюха для получения списка критериев, отключенных у параметра"""
    if request.user.is_authenticated() and request.method == "POST" and \
       request.is_ajax():
        try:
            parameter = Parameter.objects.get(pk=request.POST.get("p_id"))
        except ObjectDoesNotExist:
            raise Http404
        skip_list = []
        if not parameter.complete:
            skip_list.append(2)
        if not parameter.topical:
            skip_list.append(3)
        if not parameter.accessible:
            skip_list.append(4)
        if not parameter.hypertext:
            skip_list.append(5)
        if not parameter.document:
            skip_list.append(6)
        if not parameter.image:
            skip_list.append(7)

        return HttpResponse(simplejson.dumps(skip_list),
            mimetype='application/json')
    else:
        raise Http404
