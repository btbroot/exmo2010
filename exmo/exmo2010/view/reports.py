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
Модуль отчётов
"""

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseForbidden
from django.utils.translation import ugettext as _
from bread_crumbs.views import breadcrumbs


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
        title = current_title = _('Comments')

        crumbs = ['Home']
        breadcrumbs(request, crumbs)

        return render_to_response('exmo2010/reports/comment_list.html',
                                  {
                                      'current_title': current_title,
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
        title = current_title = _('Clarifications')

        crumbs = ['Home']
        breadcrumbs(request, crumbs)

        return render_to_response('exmo2010/reports/clarification_list.html',
                                  {
                                      'current_title': current_title,
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
        title = current_title = _('Claims')

        crumbs = ['Home']
        breadcrumbs(request, crumbs)

        return render_to_response('exmo2010/reports/claim_list.html',
                                  {
                                      'current_title': current_title,
                                      'title': title,
                                      'claims': claims,
                                  },
                                  RequestContext(request))
