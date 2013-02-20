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
Модуль отчётов
"""

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseForbidden, Http404
from django.utils.translation import ugettext as _
from django.core.paginator import Paginator, InvalidPage, EmptyPage

from exmo2010.models import Monitoring
from exmo2010.view.helpers import rating_type_parameter, rating
from exmo2010.forms import MonitoringFilterForm


def comment_list(request):
    """
    Страница сводного списка комментариев
    """
    user = request.user
    if not (user.is_active and user.profile.is_expert):
        return HttpResponseForbidden(_('Forbidden'))

    if request.is_ajax():
        comments = user.profile.get_answered_comments()
        return render_to_response(
            'exmo2010/reports/comment_list_table.html',
            {'comments': comments},
            context_instance=RequestContext(request))

    else:
        comments = user.profile.get_filtered_not_answered_comments()
        title = _('Comments')
        return render_to_response('exmo2010/reports/comment_list.html',
                                  {
                                      'title': title,
                                      'comments': comments,
                                  },
                                  RequestContext(request))


def clarification_list(request):
    """
    Страница сводного списка уточнений для аналитиков
    """
    user = request.user
    if not (user.is_active and user.profile.is_expert):
        return HttpResponseForbidden(_('Forbidden'))

    if request.is_ajax():
        clarifications = user.profile.get_closed_clarifications()
        return render_to_response(
            'exmo2010/reports/clarification_list_table.html',
            {'clarifications': clarifications},
            context_instance=RequestContext(request))

    else:
        clarifications = user.profile.get_filtered_opened_clarifications()
        title = _('Clarifications')
        return render_to_response('exmo2010/reports/clarification_list.html',
                                  {
                                      'title': title,
                                      'clarifications': clarifications,
                                  },
                                  RequestContext(request))


def claim_list(request):
    """
    Страница сводного списка претензий для аналитиков
    """
    user = request.user
    if not (user.is_active and user.profile.is_expert):
        return HttpResponseForbidden(_('Forbidden'))

    if request.is_ajax():
        claims = user.profile.get_closed_claims()
        return render_to_response(
            'exmo2010/reports/claim_list_table.html',
            {'claims': claims},
            context_instance=RequestContext(request))

    else:
        claims = user.profile.get_filtered_opened_claims()
        title = _('Claims')
        return render_to_response('exmo2010/reports/claim_list.html',
                                  {
                                      'title': title,
                                      'claims': claims,
                                  },
                                  RequestContext(request))


def monitoring_report(request, report_type='inprogress', monitoring_id=None):
    """
    Статистика по мониторингам
    """
    if report_type not in ['inprogress', 'finished']:
        raise Http404

    all_monitorings = None
    paginator_list = None

    if report_type == 'inprogress':
        all_monitorings = Monitoring.objects.exclude(
            status=Monitoring.MONITORING_PUBLISH,
            hidden=True,
        ).order_by('-rate_date')
    elif report_type == 'finished':
        all_monitorings = Monitoring.objects.exclude(
            hidden=True
        ).filter(
            status=Monitoring.MONITORING_PUBLISH
        ).order_by('-publish_date')
    if monitoring_id:
        monitorings = Monitoring.objects.filter(
            status=Monitoring.MONITORING_PUBLISH,
            pk=monitoring_id,
            hidden=False)
    else:
        monitorings = all_monitorings

        paginator = Paginator(monitorings, 10)
        try:
            page = int(request.GET.get('page', '1'))
            if page < 1:
                page = 1
        except ValueError:
            page = 1

        try:
            paginator_list = paginator.page(page)
        except (EmptyPage, InvalidPage):
            paginator_list = paginator.page(1)

        monitorings = paginator_list.object_list

    return render_to_response('exmo2010/monitoring_report.html',
                              {
                                  'paginator': paginator_list,
                                  'monitorings': monitorings,
                                  'report_type': report_type,
                                  'title': _('Monitoring statistics'),
                                  'monitoring_id': monitoring_id,
                                  'all_monitorings': all_monitorings,
                              },
                              RequestContext(request),
    )


def ratings(request):
    """
    Рейтинги
    """
    m_id = request.GET.get('monitoring')
    monitoring = None
    has_npa = False
    rating_list = None
    rating_type = None
    avg = None
    form = None
    mform = MonitoringFilterForm(request.GET)

    if m_id:
        monitoring = get_object_or_404(Monitoring, pk=m_id)
        if not request.user.has_perm('exmo2010.rating_monitoring', monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        has_npa = monitoring.has_npa
        rating_type, parameter_list, form = rating_type_parameter(request,
                                                                  monitoring,
                                                                  has_npa)
        rating_list, avg = rating(monitoring, parameters=parameter_list)

    return render_to_response('exmo2010/rating_report.html', {
        'monitoring': monitoring,
        'has_npa': has_npa,
        'object_list': rating_list,
        'rating_type': rating_type,
        'average': avg,
        'title': _('Ratings'),
        'form': form,
        'report': True,
        'mform': mform,
    }, context_instance=RequestContext(request))
