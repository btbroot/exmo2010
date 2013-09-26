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
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.utils import simplejson
from django.views.decorators.csrf import csrf_protect
from livesettings import config_value

from accounts.views import get_experts
from bread_crumbs.views import breadcrumbs
from claims.forms import *
from core.tasks import send_email
from exmo2010.models import Claim, Monitoring, Score


@csrf_protect
@login_required
def claim_manager(request, score_id, claim_id=None, method=None):
    """
    Вью для манипуляции с претензиями.

    """
    score = get_object_or_404(Score, pk=score_id)
    redirect = reverse('exmo2010:score_view', args=[score.pk])
    title = _('Add new claim for %s') % score

    if claim_id:
        claim = get_object_or_404(Claim, pk=claim_id)
    elif not method:  # create new
        if not request.user.has_perm('exmo2010.add_claim', score):
            return HttpResponseForbidden(_('Forbidden'))
        if request.method == 'GET':
            form = ClaimForm()
            form.fields['creator'].initial = request.user.pk
            form.fields['score'].initial = score.pk
        elif request.method == 'POST':
            form = ClaimForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['score'] == score and form.cleaned_data['creator'] == request.user:
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
            'claim_form.html',
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
    Добавление претензии на странице параметра.

    """
    user = request.user
    score = get_object_or_404(Score, pk=score_id)
    redirect = reverse('exmo2010:score_view', args=[score.pk, ])
    redirect += '#claims'  # Named Anchor для открытия нужной вкладки
    title = _('Add new claim for %s') % score
    if request.method == 'POST' and (
            user.has_perm('exmo2010.add_claim_score', score) or
            user.has_perm('exmo2010.answer_claim_score', score)):
        form = ClaimAddForm(request.POST, prefix="claim")
        if form.is_valid():
            # Если заполнено поле claim_id, значит это ответ на претензию
            if form.cleaned_data['claim_id'] is not None and user.has_perm('exmo2010.answer_claim_score', score):
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
                'claim_form.html',
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
    Удаление претензии (AJAX).

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
                'claim_report_table.html',
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
        'claim_report.html',
        {
            'monitoring': monitoring,
            'current_title': current_title,
            'title': title,
            'claims': claims,
            'form': form,
        },
        context_instance=RequestContext(request),
    )


def claim_list(request):
    """
    Страница сводного списка претензий для аналитиков.

    """
    user = request.user
    if not (user.is_active and user.profile.is_expert):
        return HttpResponseForbidden(_('Forbidden'))

    if request.is_ajax():
        claims = user.profile.get_closed_claims()
        return render_to_response(
            'claim_list_table.html',
            {'claims': claims},
            context_instance=RequestContext(request))

    else:
        claims = user.profile.get_filtered_opened_claims()
        title = current_title = _('Claims')

        crumbs = ['Home']
        breadcrumbs(request, crumbs)

        return render_to_response('claim_list.html',
                                  {
                                      'current_title': current_title,
                                      'title': title,
                                      'claims': claims,
                                  },
                                  RequestContext(request))


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

    recipients = list(get_experts().values_list('email', flat=True))

    if score.task.user.email and score.task.user.email not in recipients:
        recipients.append(score.task.user.email)

    for r in recipients:
        send_email.delay(r, subject, 'score_claim', context=c)


claim_was_posted_or_deleted = Signal(providing_args=["claim", "request", "creation"])
claim_was_posted_or_deleted.connect(claim_notification)
