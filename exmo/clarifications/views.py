# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _

from clarifications.forms import ClarificationReportForm
from core.utils import clean_message
from exmo2010.mail import mail_clarification
from exmo2010.models import Clarification, Monitoring, Score


@login_required
def clarification_create(request, score_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    score = get_object_or_404(Score, pk=score_pk)
    if not request.user.has_perm('exmo2010.add_clarification', score):
        raise PermissionDenied

    form = Clarification.form(request.POST)
    if form.is_valid():
        clarification = score.add_clarification(request.user, clean_message(form.cleaned_data['comment']))
        mail_clarification(request, clarification)

    redirect = reverse('exmo2010:score', args=[score.pk]) + '#clarifications'
    return HttpResponseRedirect(redirect)


@login_required
def clarification_answer(request, clarification_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    clarification = get_object_or_404(Clarification, pk=clarification_pk)
    if not request.user.has_perm('exmo2010.answer_clarification', clarification.score):
        raise PermissionDenied

    form = clarification.answer_form(request.POST)
    if form.is_valid():
        clarification.add_answer(request.user, clean_message(form.cleaned_data['answer']))
        mail_clarification(request, clarification)

    redirect = reverse('exmo2010:score', args=[clarification.score.pk]) + '#clarifications'
    return HttpResponseRedirect(redirect)


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
