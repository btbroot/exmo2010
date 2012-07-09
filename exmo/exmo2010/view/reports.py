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
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.db.models import Count
from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponseForbidden, Http404
from exmo2010.models import UserProfile, SEX_CHOICES, Score, Monitoring



SEX_CHOICES_DICT = dict(SEX_CHOICES)

def gender_stats(request):
    """
    Страница гендерной статистики.
    """
    external_users = User.objects.exclude(is_superuser=True).exclude(is_staff=True).exclude(groups__name__in=UserProfile.expert_groups)
    result = external_users.values_list('userprofile__sex').order_by('userprofile__sex').annotate(Count('userprofile__sex'))
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
        1 -- неотвеченные комментарии
        2 -- отвеченные комментарии
    """

    report_dict = {
        '1': _('Comments without answer'),
        '2': _('Comments with answer'),
    }
    if not request.user.profile.is_expert:
        return HttpResponseForbidden(_('Forbidden'))
    if report_type not in report_dict.keys():
        raise Http404

    if report_type == '1':
        queryset = request.user.profile.get_not_answered_comments()
    elif report_type == '2':
        queryset = request.user.profile.get_answered_comments()

    paginator = Paginator(queryset, settings.EXMO_PAGINATEBY)

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        comments = paginator.page(page)
    except (EmptyPage, InvalidPage):
        comments = paginator.page(paginator.num_pages)

    return render_to_response('exmo2010/comment_list.html',
        {
            'comments': comments,
            'title': report_dict[report_type],
            'report_dict': report_dict,
            'current_report': report_type,
        },
        RequestContext(request),
    )
