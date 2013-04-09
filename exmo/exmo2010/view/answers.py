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
Модуль работы с ответами анкеты
"""

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, Http404
from core.utils import UnicodeWriter
from exmo2010.models import Monitoring, Task
from exmo2010.models import Questionnaire, QQuestion


@login_required
def answers_export(request, monitoring_pk):
    """
    Экспорт ответов на анкету
    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)

    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))

    questionnaire = get_object_or_404(Questionnaire, monitoring=monitoring)
    tasks = Task.approved_tasks.filter(organization__monitoring=monitoring)

    #Нет задач для экспорта
    if not tasks.exists():
        raise Http404

    #Удобнее отлаживать без сохранения
    if hasattr(settings, 'DEBUG_EXPORT') and settings.DEBUG_EXPORT:
        response = HttpResponse(mimetype = 'text/plain')
    else:
        response = HttpResponse(mimetype = 'application/vnd.ms-excel')
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
        out = [task.organization.name, task.organization.url,]

        for answer in answers:
            out.append(answer.answer())

        writer.writerow(out)

    return response
