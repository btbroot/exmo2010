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
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.db.models import Count
from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponseForbidden, Http404
from exmo2010.models import UserProfile, SEX_CHOICES, Monitoring
from exmo2010.view.helpers import rating_type_parameter, rating
from exmo2010.forms import MonitoringFilterForm



SEX_CHOICES_DICT = dict(SEX_CHOICES)

COMMUNICATION_REPORT_TYPE_DICT = {
    1: _('Comments with answer'),
    2: _('Comments without answer'),
    3: _('Opened claims')
}


def gender_stats(request):
    """
    Страница гендерной статистики.
    """
    if (not request.user.is_authenticated() or
        not request.user.profile.is_internal()):
        raise Http404
    external_users = User.objects.exclude(is_superuser=True).exclude(
        is_staff=True).exclude(groups__name__in=UserProfile.expert_groups)
    result = external_users.values_list('userprofile__sex').order_by(
        'userprofile__sex').annotate(Count('userprofile__sex'))
    result_list = []
    for val, count in result:
        if val is not None:  # Workaround для косяка MySQL в django.
            result_list.append((SEX_CHOICES_DICT[val], count))
    result_list.append((_("Total"), external_users.count()))
    return render_to_response('exmo2010/gender_stats.html',
            {"results": result_list,}, RequestContext(request))



def comment_list(request, report_type='1'):
    """
    Страница сводного списка комментариев
    report_type:
        1 -- отвеченные комментарии
        2 -- неотвеченные комментарии
        3 -- открытые претензии
    """

    try:
        report_type = int(report_type)
    except ValueError:
        raise Http404

    if not (request.user.is_active and request.user.profile.is_expert):
        return HttpResponseForbidden(_('Forbidden'))
    if report_type not in COMMUNICATION_REPORT_TYPE_DICT.keys():
        raise Http404

    template = 'exmo2010/comment_list.html'

    if report_type == 1:
        queryset = request.user.profile.get_answered_comments()
    elif report_type == 2:
        queryset = request.user.profile.get_not_answered_comments()
    elif report_type == 3:
        queryset = request.user.profile.get_opened_claims()
        template = 'exmo2010/claim_list.html'


    paginator = Paginator(queryset, settings.EXMO_PAGINATEBY)

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

    return render_to_response(template,
        {
            'paginator': paginator_list,
            'title': COMMUNICATION_REPORT_TYPE_DICT[report_type],
            'report_dict': COMMUNICATION_REPORT_TYPE_DICT,
            'current_report': report_type,
        },
        RequestContext(request),
    )

def monitoring_report(request, report_type='inprogress', monitoring_id=None):
    if report_type not in ['inprogress', 'finished']:
        raise Http404

    all_monitorings = None
    paginator_list = None

    if report_type == 'inprogress':
        monitorings = Monitoring.objects.exclude(
            status=Monitoring.MONITORING_PUBLISH
        ).extra(select={
                'start_date': Monitoring().prepare_date_sql_inline(),
            }
        ).order_by('-start_date')[:3]
    elif report_type == 'finished':
        all_monitorings = Monitoring.objects.filter(
            status=Monitoring.MONITORING_PUBLISH
        ).extra(select={
                'start_date': Monitoring().prepare_date_sql_inline(),
            }
        ).order_by('-start_date')
        if monitoring_id:
            monitorings = Monitoring.objects.filter(
                status=Monitoring.MONITORING_PUBLISH,
                pk=monitoring_id,
            ).extra(select={
                    'start_date': Monitoring().prepare_date_sql_inline(),
                }
            ).order_by('-start_date')
            if not monitorings: raise Http404
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
    m_id = request.GET.get('monitoring')
    monitoring = None
    rating_list = None
    rating_type = None
    avg = None
    form = None
    mform = MonitoringFilterForm(request.GET)

    if m_id:
        monitoring = get_object_or_404(Monitoring, pk = m_id)
        rating_type, parameter_list, form = rating_type_parameter(request, monitoring)
        rating_list, avg = rating(monitoring, parameters=parameter_list)

    return render_to_response('exmo2010/rating_report.html', {
        'monitoring': monitoring,
        'object_list': rating_list,
        'rating_type': rating_type,
        'average': avg,
        'title': _('Ratings'),
        'form': form,
        'report': True,
        'mform': mform,
    }, context_instance=RequestContext(request))
