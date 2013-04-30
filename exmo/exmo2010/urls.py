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
from django.conf.urls.defaults import *
from django.utils.translation import ugettext as _

from bread_crumbs.views import BreadcrumbsView


urlpatterns = patterns('',

    url(r'^accounts/', include('exmo2010.custom_registration.backends.custom.urls')),

    url(r'^monitoring/', include('monitorings.urls')),

    url(r'^score/', include('scores.urls')),
    url(r'^scores/(\d+)/(print|printfull)?$', 'scores.views.score_list_by_task', name='score_list_by_task'),

    url(r'^tasks/', include('tasks.urls')),
    url(r'^task/(\d+)/history/$', 'tasks.views.task_history', name='task_history'),

    # Отчеты
    url(r'^reports/comments/$', 'custom_comments.views.comment_list', name='comment_list'),
    url(r'^reports/clarifications/$', 'clarifications.views.clarification_list', name='clarification_list'),
    url(r'^reports/claims/$', 'claims.views.claim_list', name='claim_list'),
    url(r'^reports/monitoring/$', 'monitorings.views.monitoring_report', name='monitoring_report'),
    url(r'^reports/monitoring/(\w+)/$', 'monitorings.views.monitoring_report', name='monitoring_report_type'),
    url(r'^reports/monitoring/(\w+)/(\d+)/$', 'monitorings.views.monitoring_report',
        name='monitoring_report_finished'),

    url(r'^claim/delete/$', 'claims.views.claim_delete', name='claim_delete'),
    url(r'^toggle_comment/$', 'scores.views.toggle_comment', name='toggle_comment'),
    url(r'^ratings/$', 'monitorings.views.ratings', name='ratings'),
    url(r'^help/$', BreadcrumbsView.as_view(template_name='exmo2010/help.html',
                                            get_context_data=lambda: {'current_title': _('Help')}),
        name='help'),
    url(r'^about/$', BreadcrumbsView.as_view(template_name='exmo2010/about.html',
                                             get_context_data=lambda: {'current_title': _('About')}),
        name='about'),
    url(r'^feedback/$', 'exmo2010.views.feedback', name='feedback'),
    # AJAX-вьюха для получения списка критериев, отключенных у параметра
    url(r'^get_pc/$', 'parameters.views.get_pc', name='get_pc'),
    # AJAX-вьюха для получения кода div'а для одного вопроса (c полями).
    url(r'^get_qq/$', 'questionnaire.views.get_qq', name='get_qq'),
    # AJAX-вьюха для получения кода div'а для одного вопроса (без полей).
    url(r'^get_qqt/$', 'questionnaire.views.get_qqt', name='get_qqt'),
)
