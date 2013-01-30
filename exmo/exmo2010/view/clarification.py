# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
Модуль для работы с уточнениями
"""

from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from exmo2010.models import Score, Clarification
from exmo2010.forms import ClarificationAddForm
from exmo2010.models import Monitoring
from exmo2010.forms import ClarificationReportForm
from django.http import HttpResponseForbidden


@login_required
def clarification_create(request, score_id):
    """
    Добавление уточнения на странице параметра
    """
    user = request.user
    score = get_object_or_404(Score, pk=score_id)
    redirect = reverse('exmo2010:score_view', args=[score.pk])
    redirect += '#clarifications' # Named Anchor для открытия нужной вкладки
    if request.method == 'POST' and (
        user.has_perm('exmo2010.add_clarification_score', score) or
        user.has_perm('exmo2010.answer_clarification_score', score)):
        form = ClarificationAddForm(request.POST, prefix="clarification")
        if form.is_valid():
            # Если заполнено поле clarification_id,
            # значит это ответ на уточнение
            if (form.cleaned_data['clarification_id'] is not None and
                user.has_perm('exmo2010.answer_clarification_score', score)):
                clarification_id = form.cleaned_data['clarification_id']
                clarification = get_object_or_404(Clarification,
                                                  pk=clarification_id)
                answer = form.cleaned_data['comment']
                clarification.add_answer(user, answer)
            else:
                # Если поле claim_id пустое, значит это выставление уточнения
                clarification = score.add_clarification(
                    user, form.cleaned_data['comment'])

            return HttpResponseRedirect(redirect)

        else:
            return render_to_response(
                'exmo2010/score/clarification_form.html',
                {
                    'monitoring': score.task.organization.monitoring,
                    'task': score.task,
                    'score': score,
                    'title': _('Add new claim for %s') % score,
                    'form': form,
                },
                context_instance=RequestContext(request),
            )
    else:
        raise Http404


@login_required
def clarification_report(request, monitoring_id):
    """
    Отчёт по уточнениям.
    """
    if not request.user.profile.is_expertA:
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk=monitoring_id)
    title = _('Clarifications report for "%(monitoring)s"') % {'monitoring':
                                                           monitoring.name}
    all_clarifications = Clarification.objects.filter(
        score__task__organization__monitoring=monitoring).order_by("open_date")
    opened_clarifications = all_clarifications.filter(close_date__isnull=True)
    closed_clarifications = all_clarifications.filter(close_date__isnull=False)
    addressee_id_list = all_clarifications.select_related(
        'score__task__user').values_list('id', flat=True)
    creator_id_list = all_clarifications.order_by().values_list(
        "creator", flat=True).distinct()

    if request.method == "POST":
        form = ClarificationReportForm(request.POST,
                                       creator_id_list=creator_id_list,
                                       addressee_id_list=addressee_id_list)
        if form.is_valid():
            cd = form.cleaned_data
            creator_id = int(cd["creator"])
            addressee_id = int(cd["addressee"])
            if creator_id != 0:
                opened_clarifications = opened_clarifications.filter(
                    creator__id=creator_id)
                closed_clarifications = closed_clarifications.filter(
                    creator__id=creator_id)
            if addressee_id != 0:
                opened_clarifications = opened_clarifications.filter(
                    score__task__user__id=addressee_id)
                closed_clarifications = closed_clarifications.filter(
                    score__task__user__id=addressee_id)
    else:
        form = ClarificationReportForm(creator_id_list=creator_id_list,
            addressee_id_list=addressee_id_list)

    return render_to_response(
        'exmo2010/reports/clarification_report.html',
        {
            'monitoring': monitoring,
            'title': title,
            'opened_clarifications': opened_clarifications,
            'closed_clarifications': closed_clarifications,
            'form': form,
            },
        context_instance=RequestContext(request),
    )