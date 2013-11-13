# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
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
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.dispatch import Signal
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
from livesettings import config_value

from accounts.views import get_experts
from clarifications.forms import ClarificationReportForm, ClarificationAddForm
from core.tasks import send_email
from exmo2010.models import Clarification, Monitoring, Score


@login_required
def clarification_create(request, score_pk):
    """
    Добавление уточнения на странице параметра.

    """
    user = request.user
    score = get_object_or_404(Score, pk=score_pk)
    redirect = reverse('exmo2010:score_view', args=[score.pk])
    redirect += '#clarifications'  # Named Anchor для открытия нужной вкладки
    title = _('Add new claim for %s') % score
    if request.method == 'POST' and (
        user.has_perm('exmo2010.add_clarification_score', score) or
            user.has_perm('exmo2010.answer_clarification_score', score)):
        form = ClarificationAddForm(request.POST, prefix="clarification")
        if form.is_valid():
            # Если заполнено поле clarification_id,
            # значит это ответ на уточнение
            if form.cleaned_data['clarification_id'] is not None and \
                    user.has_perm('exmo2010.answer_clarification_score', score):
                clarification_id = form.cleaned_data['clarification_id']
                clarification = get_object_or_404(Clarification,
                                                  pk=clarification_id)
                answer = form.cleaned_data['comment']
                clarification.add_answer(user, answer)
            else:
                # Если поле claim_id пустое, значит это выставление уточнения
                clarification = score.add_clarification(
                    user, form.cleaned_data['comment'])

            clarification_was_posted.send(
                sender=Clarification.__class__,
                clarification=clarification,
                request=request,
            )

            return HttpResponseRedirect(redirect)
        else:
            return TemplateResponse(request, 'clarification_form.html', {
                'monitoring': score.task.organization.monitoring,
                'task': score.task,
                'score': score,
                'title': title,
                'form': form,
            })
    else:
        raise Http404


@login_required
def clarification_report(request, monitoring_pk):
    """
    Отчёт по уточнениям.

    """
    if not request.user.profile.is_expertA:
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    all_clarifications = Clarification.objects.filter(
        score__task__organization__monitoring=monitoring).order_by("open_date")
    title = _('Clarifications report for "%s"') % monitoring.name

    if request.is_ajax():
        creator_id = request.REQUEST.get('creator_id')
        addressee_id = request.REQUEST.get('addressee_id')
        if creator_id is not None and addressee_id is not None:
            creator_id = int(creator_id)
            addressee_id = int(addressee_id)
            clarifications = all_clarifications.filter(close_date__isnull=False)
            if creator_id != 0:
                clarifications = clarifications.filter(creator__id=creator_id)
            if addressee_id != 0:
                clarifications = clarifications.filter(score__task__user__id=addressee_id)
            return TemplateResponse(request, 'clarification_report_table.html', {
                'clarifications': clarifications
            })
        else:
            raise Http404

    clarifications = all_clarifications.filter(close_date__isnull=True)

    addressee_id_list = all_clarifications.order_by().values_list(
        'score__task__user', flat=True).distinct()
    creator_id_list = all_clarifications.order_by().values_list(
        "creator", flat=True).distinct()

    if request.method == "POST":
        form = ClarificationReportForm(
            request.POST,
            creator_id_list=creator_id_list,
            addressee_id_list=addressee_id_list
        )
        if form.is_valid():
            cd = form.cleaned_data
            creator_id = int(cd["creator"])
            addressee_id = int(cd["addressee"])
            if creator_id != 0:
                clarifications = clarifications.filter(
                    creator__id=creator_id)
            if addressee_id != 0:
                clarifications = clarifications.filter(
                    score__task__user__id=addressee_id)
    else:
        form = ClarificationReportForm(
            creator_id_list=creator_id_list,
            addressee_id_list=addressee_id_list
        )

    return TemplateResponse(request, 'clarification_report.html', {
        'monitoring': monitoring,
        'title': title,
        'clarifications': clarifications,
        'form': form,
    })


def clarification_list(request):
    """
    Страница сводного списка уточнений для аналитиков.

    """
    user = request.user
    if not (user.is_active and user.profile.is_expert):
        return HttpResponseForbidden(_('Forbidden'))

    if request.is_ajax():
        clarifications = user.profile.get_closed_clarifications()
        return TemplateResponse(request, 'clarification_list_table.html', {
            'clarifications': clarifications
        })

    else:
        clarifications = user.profile.get_filtered_opened_clarifications()
        title = _('Clarifications')

        return TemplateResponse(request, 'clarification_list.html', {
            'title': title,
            'clarifications': clarifications
        })


def clarification_notification(sender, **kwargs):
    clarification = kwargs['clarification']
    request = kwargs['request']
    score = clarification.score

    subject = '%(prefix)s%(monitoring)s - %(org)s: %(code)s - %(msg)s' % {
        'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
        'monitoring': score.task.organization.monitoring,
        'org': score.task.organization.name.split(':')[0],
        'code': score.parameter.code,
        'msg': _('New clarification')
    }

    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http',
                         request.get_host(),
                         reverse('exmo2010:score_view', args=[score.pk]))

    c = {'score': score,
         'clarification': clarification,
         'url': url}

    recipients = list(get_experts().values_list('email', flat=True))

    if score.task.user.email and score.task.user.email not in recipients:
        recipients.append(score.task.user.email)

    for r in recipients:
        send_email.delay(r, subject, 'score_clarification', context=c)


clarification_was_posted = Signal(providing_args=["clarification", "request"])
clarification_was_posted.connect(clarification_notification)
