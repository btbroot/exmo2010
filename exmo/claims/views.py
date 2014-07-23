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
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _

from claims.forms import ClaimReportForm
from core.response import JSONResponse
from core.utils import clean_message
from exmo2010.mail import mail_claim_deleted, mail_claim_new
from exmo2010.models import Claim, Monitoring, Score


@login_required
def claim_create(request, score_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    score = get_object_or_404(Score, pk=score_pk)
    if not request.user.has_perm('exmo2010.add_claim', score):
        raise PermissionDenied

    form = Claim.form(request.POST)
    if form.is_valid():
        claim = score.add_claim(request.user, clean_message(form.cleaned_data['comment']))
        mail_claim_new(request, claim)

    redirect = reverse('exmo2010:score', args=[score.pk]) + '#claims'
    return HttpResponseRedirect(redirect)


@login_required
def claim_answer(request, claim_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    claim = get_object_or_404(Claim, pk=claim_pk)
    if not request.user.has_perm('exmo2010.answer_claim', claim.score):
        raise PermissionDenied

    form = claim.answer_form(request.POST)
    if form.is_valid():
        claim.add_answer(request.user, clean_message(form.cleaned_data['answer']))
        mail_claim_new(request, claim)

    redirect = reverse('exmo2010:score', args=[claim.score.pk]) + '#claims'
    return HttpResponseRedirect(redirect)


@login_required
def claim_delete(request):
    """
    Удаление претензии (AJAX).

    """
    if request.is_ajax() and request.method == 'POST':
        claim_id = request.POST.get('pk')
        if claim_id is not None:
            claim = get_object_or_404(Claim, pk=claim_id)
            if not request.user.has_perm('exmo2010.delete_claim', claim.score):
                raise PermissionDenied
            claim.delete()
            mail_claim_deleted(request, claim)
            return JSONResponse(success=True)
    raise Http404


@login_required
def claim_report(request, monitoring_pk):
    """
    Отчёт по претензиям.

    """
    if not request.user.profile.is_expertA:
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    all_claims = Claim.objects.filter(
        score__task__organization__monitoring=monitoring).order_by("open_date")

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
            return TemplateResponse(request, 'claim_report_table.html', {'claims': claims})
        else:
            raise Http404

    claims = all_claims.filter(close_date__isnull=True)

    addressee_id_list = all_claims.order_by().values_list(
        "addressee", flat=True).distinct()
    creator_id_list = all_claims.order_by().values_list(
        "creator", flat=True).distinct()

    if request.method == "POST":
        form = ClaimReportForm(
            request.POST,
            creator_id_list=creator_id_list,
            addressee_id_list=addressee_id_list
        )
        if form.is_valid():
            cd = form.cleaned_data
            creator_id = int(cd["creator"])
            addressee_id = int(cd["addressee"])
            if creator_id != 0:
                claims = claims.filter(creator__id=creator_id)
            if addressee_id != 0:
                claims = claims.filter(addressee__id=addressee_id)
    else:
        form = ClaimReportForm(
            creator_id_list=creator_id_list,
            addressee_id_list=addressee_id_list
        )

    return TemplateResponse(request, 'claim_report.html', {
        'monitoring': monitoring,
        'title': _('Claims report for "%s"') % monitoring,
        'claims': claims,
        'form': form,
    })


def claim_list(request):
    """
    Страница сводного списка претензий для аналитиков.

    """
    user = request.user
    if not (user.is_active and user.profile.is_expert):
        return HttpResponseForbidden(_('Forbidden'))

    if request.is_ajax():
        claims = user.profile.get_closed_claims()
        return TemplateResponse(request, 'claim_list_table.html', {'claims': claims})
    else:
        claims = user.profile.get_filtered_opened_claims()
        return TemplateResponse(request, 'claim_list.html', {
            'title': _('Claims'),
            'claims': claims,
        })


