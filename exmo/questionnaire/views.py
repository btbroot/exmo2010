# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt

from .forms import QuestionnaireDynForm
from exmo2010.models import Monitoring, Task, LicenseTextFragments
from exmo2010.models import Questionnaire, QAnswer, QQuestion, QUESTION_TYPE_CHOICES, AnswerVariant
from core.utils import UnicodeWriter


@login_required
@csrf_exempt
def add_questionnaire(request, monitoring_pk):
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
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring) or \
            monitoring.has_questions():
        raise PermissionDenied
    if request.method == "POST":
        if request.is_ajax():
            try:
                questionset = json.loads(request.POST.get("questionaire"))
            except ValueError:
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
            raise PermissionDenied
    else:
        title = _('Edit monitoring %s') % monitoring
        # title0 - потому что переменную title ждет темплейт base.html и
        # использует не так, как мне тут нужно.

        return TemplateResponse(request, 'add_questionnaire.html', {
            "monitoring": monitoring,
            "title0": title
        })


@login_required
def answers_export(request, monitoring_pk):
    """
    Экспорт ответов на анкету.

    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)

    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        raise PermissionDenied

    questionnaire = get_object_or_404(Questionnaire, monitoring=monitoring)
    tasks = Task.approved_tasks.filter(organization__monitoring=monitoring)

    #Нет задач для экспорта
    if not tasks.exists():
        raise Http404

    #Удобнее отлаживать без сохранения
    if hasattr(settings, 'DEBUG_EXPORT') and settings.DEBUG_EXPORT:
        response = HttpResponse(mimetype='text/plain')
    else:
        response = HttpResponse(mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=anketa-%s.csv' % monitoring.pk
    response.encoding = 'UTF-16'
    writer = UnicodeWriter(response)

    header = ['#organization', 'url']
    questions = QQuestion.objects.filter(questionnaire=questionnaire)
    for question in questions:
        header.append(question.question)
    writer.writerow(header)

    #Это работает только если анкета заполнена целиком. Но иного по workflow быть не должно.
    for task in tasks:
        answers = task.qanswer_set.filter(question__questionnaire=questionnaire)
        out = [task.organization.name, task.organization.url]

        for answer in answers:
            out.append(answer.answer())

        writer.writerow(out)

    license = LicenseTextFragments.objects.filter(pk='license')
    if license:
        writer.writerow([u'#%s' % license[0].csv_footer])

    return response


@login_required
def ajax_get_qqt(request):
    """
    AJAX-вьюха для получения кода div'а для одного вопроса (без полей).

    """
    if request.method == "GET" and request.is_ajax():
        return TemplateResponse(request, 'question_div2.html')

    raise PermissionDenied


@login_required
def ajax_get_qq(request):
    """
    AJAX-вьюха для получения кода div'а для одного вопроса (c полями).

    """
    if request.method == "GET" and request.is_ajax():
        return TemplateResponse(request, 'question_div.html', {"choices": QUESTION_TYPE_CHOICES})

    raise PermissionDenied


@login_required
def post_questionnaire(request, task_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(permitted_methods=['POST'])

    task = get_object_or_404(Task, pk=task_pk)
    if not request.user.has_perm('exmo2010.fill_task', task):
        raise PermissionDenied

    questionnaire = get_object_or_404(Questionnaire, monitoring=task.organization.monitoring)
    questions = questionnaire.qquestion_set.order_by("pk")

    questionnaire_form = QuestionnaireDynForm(request.POST, questions=questions, task=task)
    if questionnaire_form.is_valid():
        for answ in questionnaire_form.cleaned_data.items():
            if answ[0].startswith("q_"):
                try:
                    q_id = int(answ[0][2:])
                    question_obj = QQuestion.objects.get(pk=q_id)
                except (ValueError, ObjectDoesNotExist):
                    continue
                if answ[1]:  # Непустое значение ответа.
                    answer = QAnswer.objects.get_or_create(task=task, question=question_obj)[0]
                    if question_obj.qtype == 0:
                        answer.text_answer = answ[1]
                        answer.save()
                    elif question_obj.qtype == 1:
                        answer.numeral_answer = answ[1]
                        answer.save()
                    elif question_obj.qtype == 2:
                        answer.variance_answer = answ[1]
                        answer.save()
                else:  # Пустой ответ.
                    try:
                        answer = QAnswer.objects.get(task=task, question=question_obj)
                    except ObjectDoesNotExist:
                        continue
                    else:
                        answer.delete()

        return HttpResponseRedirect(request.POST.get('next') or reverse('exmo2010:task_scores', args=[task.pk]))

    return HttpResponse()
