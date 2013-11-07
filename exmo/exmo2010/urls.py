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
import types

from django.conf.urls import patterns, url, include

import reversion

from exmo2010.views import HelpView, AboutView, OpenDataView
from monitorings.views import MonitoringManagerView
from organizations.views import OrganizationManagerView
from parameters.views import ParameterManagerView
from scores.views import ScoreAddView, ScoreEditView, ScoreDeleteView, ScoreDetailView
from tasks.views import TaskManagerView


def named_urls(module, *pattern_tuples):
    '''
    Wrapper around django.conf.urls.patterns which can guess url name from view and
    automatically converts GenericView classes to views
    Positional args are pattern_tuples:
        (pattern, view, name)
        or
        (pattern, view)
    If the name is omitted, it will be the same as view class or view function name
    '''
    result_patterns = []
    for p_tuple in pattern_tuples:
        try:
            regex, view, name = p_tuple
        except ValueError:
            regex, view = p_tuple
            if isinstance(view, types.TypeType):
                name = view.__name__
            elif isinstance(view, (str, unicode)):
                name = view.split('.')[-1]
            else:
                name = None

        if isinstance(view, types.TypeType):
            view = view.as_view()

        result_patterns.append(url(regex, view, name=name))

    return patterns(module, *result_patterns)


scores_patterns = named_urls('scores.views',
    (r'^(?P<score_pk>\d+)/$', 'score_view'),
    (r'^(?P<task_pk>\d+)_(?P<parameter_pk>\d+)/$', ScoreAddView, 'score_add'),
    (r'^(?P<score_pk>\d+)_(?P<method>\w+)/$', 'score_manager'),
    (r'^(?P<score_pk>\d+)/edit/$', reversion.create_revision()(ScoreEditView.as_view()), 'score_edit'),
    (r'^(?P<score_pk>\d+)/delete/$', reversion.create_revision()(ScoreDeleteView.as_view()), 'score_delete'),
    (r'^(?P<score_pk>\d+)/detail/$', ScoreDetailView, 'score_detail'),
    (r'^(?P<score_pk>\d+)/comment/add/$', 'score_add_comment'),
    (r'^rating_update$', 'ratingUpdate'),
)

scores_patterns += named_urls('',
    (r'^(?P<score_pk>\d+)/claim/create/$', 'claims.views.claim_create'),
    (r'^(?P<score_pk>\d+)/clarification/create/$', 'clarifications.views.clarification_create'),
)

monitoring_patterns = named_urls('monitorings.views',
    (r'^$', 'monitoring_list'),
    (r'^add/$', 'monitoring_add'),
    (r'^(?P<monitoring_pk>\d+)/by_criteria_mass_export/$', 'monitoring_by_criteria_mass_export'),
    (r'^(?P<monitoring_pk>\d+)/comment_report/$', 'monitoring_comment_report'),
    (r'^(?P<monitoring_pk>\d+)/experts/$', 'monitoring_by_experts'),
    (r'^(?P<monitoring_pk>\d+)/organization_export/$', 'monitoring_organization_export'),
    (r'^(?P<monitoring_pk>\d+)/organization_import/$', 'monitoring_organization_import'),
    (r'^(?P<monitoring_pk>\d+)/parameter_export/$', 'monitoring_parameter_export'),
    (r'^(?P<monitoring_pk>\d+)/parameter_filter/$', 'monitoring_parameter_filter'),
    (r'^(?P<monitoring_pk>\d+)/parameter_found_report/$', 'monitoring_parameter_found_report'),
    (r'^(?P<monitoring_pk>\d+)/parameter_import/$', 'monitoring_parameter_import'),
    (r'^(?P<monitoring_pk>\d+)/rating/$', 'monitoring_rating'),
    (r'^(?P<monitoring_pk>\d+)/set_npa_params/$', 'set_npa_params'),
    (r'^(?P<monitoring_pk>\d+)_(?P<method>\w+)/$', MonitoringManagerView, 'monitoring_manager'),
    (r'^(?P<monitoring_pk>\d+)/export/$', 'monitoring_export'),
)

monitoring_patterns += named_urls('tasks.views',
    (r'^(?P<monitoring_pk>\d+)/mass_assign_tasks/$', 'task_mass_assign_tasks'),
    (r'^(?P<monitoring_pk>\d+)/organization/(?P<org_pk>\d+)/task/add/$', 'task_add'),
    (r'^(?P<monitoring_pk>\d+)/organization/(?P<org_pk>\d+)/task/(?P<task_pk>\d+)_(?P<method>\w+)/$',
        TaskManagerView, 'task_manager'),
    (r'^(?P<monitoring_pk>\d+)/organization/(?P<org_pk>\d+)/tasks/$', 'tasks_by_monitoring_and_organization'),
    (r'^(?P<monitoring_pk>\d+)/task/add/$', 'task_add'),
    (r'^(?P<monitoring_pk>\d+)/tasks/$', 'tasks_by_monitoring'),
)

monitoring_patterns += named_urls('organizations.views',
    (r'^(?P<monitoring_pk>\d+)/organization/(?P<org_pk>\d+)_(?P<method>\w+)/$',
        OrganizationManagerView, 'organization_manager'),
    (r'^(?P<monitoring_pk>\d+)/organizations/$', 'organization_list'),
)

monitoring_patterns += named_urls('questionnaire.views',
    (r'^(?P<monitoring_pk>\d+)/add_questionnaire/$', 'add_questionnaire'),
    (r'^(?P<monitoring_pk>\d+)/answers_export/$', 'answers_export', 'monitoring_answers_export'),
)

monitoring_patterns += named_urls('',
    (r'^(?P<monitoring_pk>\d+)/claims/$', 'claims.views.claim_report'),
    (r'^(?P<monitoring_pk>\d+)/clarifications/$', 'clarifications.views.clarification_report'),
)


tasks_patterns = named_urls('tasks.views',
    (r'^$', 'tasks'),
    (r'^task/(?P<task_pk>\d+)_(?P<method>\w+)/$',
        reversion.create_revision()(TaskManagerView.as_view()), 'task_manager'),
    (r'^taskexport/(?P<task_pk>\d+)/$', 'task_export'),
    (r'^taskimport/(?P<task_pk>\d+)/$', 'task_import'),
)

tasks_patterns += named_urls('parameters.views',
    (r'^task/(?P<task_pk>\d+)/parameter/(?P<parameter_pk>\d+)_(?P<method>\w+)/$',
        ParameterManagerView, 'parameter_manager'),
    (r'^task/(?P<task_pk>\d+)/parameter/add/$', 'parameter_add',),
)


urlpatterns = named_urls('',
    (r'^accounts/', include('exmo2010.custom_registration.backends.custom.urls')),

    (r'^monitoring/', include(monitoring_patterns)),

    (r'^score/', include(scores_patterns)),
    (r'^scores/(?P<task_pk>\d+)/(?P<print_report_type>print|printfull)?$', 'scores.views.score_list_by_task'),

    (r'^tasks/', include(tasks_patterns)),
    (r'^task/(?P<task_pk>\d+)/history/$', 'tasks.views.task_history'),

    # Отчеты
    (r'^reports/comments/$', 'custom_comments.views.comment_list'),
    (r'^reports/clarifications/$', 'clarifications.views.clarification_list'),
    (r'^reports/claims/$', 'claims.views.claim_list'),
    (r'^reports/monitoring/$', 'monitorings.views.monitoring_report'),
    (r'^reports/monitoring/(?P<report_type>inprogress|finished)/$',
        'monitorings.views.monitoring_report', 'monitoring_report_type'),
    (r'^reports/monitoring/(?P<report_type>inprogress|finished)/(?P<monitoring_pk>\d+)/$',
        'monitorings.views.monitoring_report', 'monitoring_report_finished'),

    (r'^claim/delete/$', 'claims.views.claim_delete'),
    (r'^toggle_comment/$', 'scores.views.toggle_comment'),
    (r'^ratings/$', 'monitorings.views.ratings'),
    (r'^help/$', HelpView, 'help'),
    (r'^about/$', AboutView, 'about'),

    (r'^opendata/$', OpenDataView, 'opendata'),
    (r'^feedback/$', 'exmo2010.views.feedback'),
    # AJAX-вьюха для получения списка критериев, отключенных у параметра
    (r'^get_pc/$', 'parameters.views.get_pc'),
    # AJAX-вьюха для получения кода div'а для одного вопроса (c полями).
    (r'^get_qq/$', 'questionnaire.views.get_qq'),
    # AJAX-вьюха для получения кода div'а для одного вопроса (без полей).
    (r'^get_qqt/$', 'questionnaire.views.get_qqt'),
)
