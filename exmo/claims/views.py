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
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.dispatch import Signal
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
from django.utils import simplejson
from livesettings import config_value

from claims.forms import ClaimAddForm, ClaimReportForm
from core.tasks import send_email
from exmo2010.models import Claim, Monitoring, Score, UserProfile


@login_required
def claim_create(request, score_pk):
    """
    Добавление претензии на странице параметра.

    """
    user = request.user
    score = get_object_or_404(Score, pk=score_pk)
    redirect = reverse('exmo2010:score_view', args=[score.pk, ])
    redirect += '#claims'  # Named Anchor для открытия нужной вкладки
    title = _('Add new claim for %s') % score
    if request.method == 'POST':
        form = ClaimAddForm(request.POST, prefix="claim")
        if form.is_valid():
            if form.cleaned_data['claim_id'] is not None:
                # Если заполнено поле claim_id, значит это ответ на претензию
                if not user.has_perm('exmo2010.answer_claim_score', score):
                    raise PermissionDenied
                claim_id = form.cleaned_data['claim_id']
                claim = get_object_or_404(Claim, pk=claim_id)
                answer = form.cleaned_data['comment']
                claim.add_answer(user, answer)
            else:
                # Если поле claim_id пустое, значит это выставление претензии
                if not user.has_perm('exmo2010.add_claim_score', score):
                    raise PermissionDenied
                claim = score.add_claim(user, form.cleaned_data['comment'])

            claim_was_posted_or_deleted.send(
                sender=Claim.__class__,
                claim=claim,
                request=request,
                creation=True,
            )
            return HttpResponseRedirect(redirect)
        else:
            return TemplateResponse(request, 'claim_form.html', {
                'monitoring': score.task.organization.monitoring,
                'task': score.task,
                'score': score,
                'title': title,
                'form': form,
            })
    else:
        raise Http404


@login_required
def claim_delete(request):
    """
    Удаление претензии (AJAX).

    """
    if request.is_ajax() and request.method == 'POST':
        claim_id = request.POST.get('pk')
        if claim_id is not None:
            claim = get_object_or_404(Claim, pk=claim_id)
            if not request.user.has_perm('exmo2010.delete_claim_score', claim.score):
                raise PermissionDenied
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


def claim_notification(sender, **kwargs):
    claim = kwargs['claim']
    request = kwargs['request']
    creation = kwargs['creation']
    score = claim.score

    theme = _('New claim') if creation else _('Delete claim')

    subject = '%(prefix)s%(monitoring)s - %(org)s: %(code)s - %(theme)s' % {
        'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
        'monitoring': score.task.organization.monitoring,
        'org': score.task.organization.name.split(':')[0],
        'code': score.parameter.code,
        'theme': theme,
    }

    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http',
                         request.get_host(),
                         reverse('exmo2010:score_view',
                                 args=[score.pk]))

    c = {'score': score,
         'claim': claim,
         'url': url,
         'creation': creation,
         'current_user': request.user.userprofile.legal_name,
         }

    recipients = User.objects.exclude(email__exact='').exclude(email__isnull=True).distinct().filter(
        Q(groups__name=UserProfile.expertA_group, is_active=True) | Q(pk=score.task.user.pk))

    for r in recipients.values_list('email', flat=True):
        send_email.delay(r, subject, 'score_claim', context=c)


claim_was_posted_or_deleted = Signal(providing_args=["claim", "request", "creation"])
claim_was_posted_or_deleted.connect(claim_notification)
