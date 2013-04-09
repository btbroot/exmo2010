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
Модуль для работы с претензиями
"""

from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.utils import simplejson
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseRedirect, HttpResponse
from django.http import HttpResponseForbidden, Http404
from django.template import RequestContext
from django.core.urlresolvers import reverse
from bread_crumbs.views import breadcrumbs
from exmo2010.signals import claim_was_posted_or_deleted
from exmo2010.models import Score, Claim
from exmo2010.models import Monitoring
from exmo2010.forms import ClaimForm, ClaimAddForm
from exmo2010.forms import ClaimReportForm


@csrf_protect
@login_required
def claim_manager(request, score_id, claim_id=None, method=None):
    """
    Вью для манипуляции с претензиями
    """
    score = get_object_or_404(Score, pk=score_id)
    redirect = reverse('exmo2010:score_view', args=[score.pk])
    title = _('Add new claim for %s') % score

    if claim_id:
        claim = get_object_or_404(Claim, pk=claim_id)
    elif not method: #create new
        if not request.user.has_perm('exmo2010.add_claim', score):
            return HttpResponseForbidden(_('Forbidden'))
        if request.method == 'GET':
            form = ClaimForm()
            form.fields['creator'].initial = request.user.pk
            form.fields['score'].initial = score.pk
        elif request.method == 'POST':
            form = ClaimForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['score'] == score and form.cleaned_data[
                    'creator'] == request.user:
                    claim = score.add_claim(request.user,
                                            form.cleaned_data['comment'])
                    claim_was_posted_or_deleted.send(
                        sender=Claim.__class__,
                        claim=claim,
                        request=request,
                        creation=True,
                    )
                    return HttpResponseRedirect(redirect)

        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList', 'ScoreView']
        breadcrumbs(request, crumbs, score)
        current_title = _('Edit claim')

        return render_to_response(
            'exmo2010/score/claim_form.html',
            {
                'monitoring': score.task.organization.monitoring,
                'task': score.task,
                'score': score,
                'current_title': current_title,
                'title': title,
                'form': form,
            },
            context_instance=RequestContext(request),
        )


@login_required
def claim_create(request, score_id):
    """
    Добавление претензии на странице параметра
    """
    user = request.user
    score = get_object_or_404(Score, pk=score_id)
    redirect = reverse('exmo2010:score_view', args=[score.pk, ])
    redirect += '#claims' # Named Anchor для открытия нужной вкладки
    title = _('Add new claim for %s') % score
    if request.method == 'POST' and (
            user.has_perm('exmo2010.add_claim_score', score) or
            user.has_perm('exmo2010.answer_claim_score', score)):
        form = ClaimAddForm(request.POST, prefix="claim")
        if form.is_valid():
            # Если заполнено поле claim_id, значит это ответ на претензию
            if (form.cleaned_data['claim_id'] is not None
                and user.has_perm('exmo2010.answer_claim_score', score)):
                claim_id = form.cleaned_data['claim_id']
                claim = get_object_or_404(Claim, pk=claim_id)
                answer = form.cleaned_data['comment']
                claim.add_answer(user, answer)
            else:
            # Если поле claim_id пустое, значит это выставление претензии
                claim = score.add_claim(user, form.cleaned_data['comment'])

            claim_was_posted_or_deleted.send(
                sender=Claim.__class__,
                claim=claim,
                request=request,
                creation=True,
            )
            return HttpResponseRedirect(redirect)
        else:

            crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList', 'ScoreView']
            breadcrumbs(request, crumbs, score)
            current_title = _('Create claim')

            return render_to_response(
                'exmo2010/score/claim_form.html',
                {
                    'monitoring': score.task.organization.monitoring,
                    'task': score.task,
                    'score': score,
                    'current_title': current_title,
                    'title': title,
                    'form': form,
                },
                context_instance=RequestContext(request),
            )
    else:
        raise Http404


@login_required
def claim_delete(request):
    """
    Удаление претензии (AJAX)
    """
    if request.is_ajax() and request.method == 'POST':
        claim_id = request.POST.get('pk')
        if claim_id is not None:
            claim = get_object_or_404(Claim, pk=claim_id)
            claim.delete()
            result = simplejson.dumps({'success': True})

            claim_was_posted_or_deleted.send(
                sender=Claim.__class__,
                claim=claim,
                request=request,
                creation=False,
            )

            return HttpResponse(result, mimetype='application/json')
    raise Http404


@login_required
def claim_report(request, monitoring_id):
    """
    Отчёт по претензиям.
    """
    if not request.user.profile.is_expertA:
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk=monitoring_id)
    all_claims = Claim.objects.filter(
        score__task__organization__monitoring=monitoring).order_by("open_date")
    title = _('Claims report for "%s"') % monitoring

    if request.is_ajax():
        creator_id = request.REQUEST.get('creator_id')
        addressee_id = request.REQUEST.get('addressee_id')
        if creator_id is not None and addressee_id is not None:
            creator_id = int(creator_id)
            addressee_id = int(addressee_id)
            claims = all_claims.filter(close_date__isnull=False)
            if creator_id != 0:
                claims = claims.filter(creator__id=creator_id)
            if addressee_id != 0:
                claims = claims.filter(addressee__id=addressee_id)
            return render_to_response(
                'exmo2010/reports/claim_report_table.html',
                {'claims': claims},
                context_instance=RequestContext(request))
        else:
            raise Http404

    claims = all_claims.filter(close_date__isnull=True)

    addressee_id_list = all_claims.order_by().values_list(
        "addressee", flat=True).distinct()
    creator_id_list = all_claims.order_by().values_list(
        "creator", flat=True).distinct()

    if request.method == "POST":
        form = ClaimReportForm(request.POST,
                               creator_id_list=creator_id_list,
                               addressee_id_list=addressee_id_list)
        if form.is_valid():
            cd = form.cleaned_data
            creator_id = int(cd["creator"])
            addressee_id = int(cd["addressee"])
            if creator_id != 0:
                claims = claims.filter(creator__id=creator_id)
            if addressee_id != 0:
                claims = claims.filter(addressee__id=addressee_id)
    else:
        form = ClaimReportForm(creator_id_list=creator_id_list,
                               addressee_id_list=addressee_id_list)

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs)

    if request.expert:
        current_title = _('Monitoring cycle')
    else:
        current_title = _('Rating') if monitoring.status == 5 else _('Tasks')

    return render_to_response(
        'exmo2010/reports/claim_report.html',
        {
            'monitoring': monitoring,
            'current_title': current_title,
            'title': title,
            'claims': claims,
            'form': form,
        },
        context_instance=RequestContext(request),
    )
