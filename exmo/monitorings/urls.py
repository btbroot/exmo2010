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
from django.conf.urls.defaults import *
from monitorings.views import MonitoringManagerView
from organizations.views import OrganizationManagerView
from tasks.views import TaskManagerView

urlpatterns = \
    patterns('monitorings.views',
             url(r'^$', 'monitoring_list', name='monitoring_list'),
             url(r'^add/$', 'monitoring_add', name='monitoring_add'),
             url(r'^(\d+)/by_criteria_mass_export/$', 'monitoring_by_criteria_mass_export',
                 name='monitoring_by_criteria_mass_export'),
             url(r'^(\d+)/comment_report/$', 'monitoring_comment_report', name='monitoring_comment_report'),
             url(r'^(\d+)/experts/$', 'monitoring_by_experts', name='monitoring_by_experts'),
             url(r'^(\d+)/organization_export/$', 'monitoring_organization_export',
                 name='monitoring_organization_export'),
             url(r'^(\d+)/organization_import/$', 'monitoring_organization_import',
                 name='monitoring_organization_import'),
             url(r'^(\d+)/parameter_export/$', 'monitoring_parameter_export', name='monitoring_parameter_export'),
             url(r'^(\d+)/parameter_filter/$', 'monitoring_parameter_filter', name='monitoring_parameter_filter'),
             url(r'^(\d+)/parameter_found_report/$', 'monitoring_parameter_found_report',
                 name='monitoring_parameter_found_report'),
             url(r'^(\d+)/parameter_import/$', 'monitoring_parameter_import', name='monitoring_parameter_import'),
             url(r'^(\d+)/rating/$', 'monitoring_rating', name='monitoring_rating'),
             url(r'^(\d+)/set_npa_params/$', 'set_npa_params', name='set_npa_params'),
             url(r'^(?P<pk>\d+)_(?P<method>\w+)/$', MonitoringManagerView.as_view(), name='monitoring_manager'),
             url(r'^(\d+)/export/$', 'monitoring_export',
                 name='monitoring_export'),
             )

urlpatterns += \
    patterns('tasks.views',
             url(r'^(\d+)/mass_assign_tasks/$', 'task_mass_assign_tasks', name='task_mass_assign_tasks'),
             url(r'^(\d+)/organization/(\d+)/task/add/$', 'task_add', name='task_add'),
             url(r'^(?P<monitoring_id>\d+)/organization/(?P<organization_id>\d+)/task/(?P<pk>\d+)_(?P<method>\w+)/$', TaskManagerView.as_view(), name='task_manager'),
             url(r'^(\d+)/organization/(\d+)/tasks/$', 'tasks_by_monitoring_and_organization',
                 name='tasks_by_monitoring_and_organization'),
             url(r'^(\d+)/task/add/$', 'task_add', name='task_add'),
             url(r'^(\d+)/tasks/$', 'tasks_by_monitoring', name='tasks_by_monitoring'),
             )

urlpatterns += \
    patterns('organizations.views',
             url(r'^(?P<monitoring_id>\d+)/organization/(?P<pk>\d+)_(?P<method>\w+)/$',
                 OrganizationManagerView.as_view(),
                 name='organization_manager'),
             url(r'^(\d+)/organizations/$', 'organization_list', name='organization_list'),
             )

urlpatterns += \
    patterns('questionnaire.views',
             url(r'^(\d+)/add_questionnaire/$', 'add_questionnaire', name='add_questionnaire'),
             url(r'^(\d+)/answers_export/$', 'answers_export', name='monitoring_answers_export'),
             )

urlpatterns += \
    patterns('claims.views',
             url(r'^(\d+)/claims/$', 'claim_report', name='claim_report'),
             )

urlpatterns += \
    patterns('clarifications.views',
             url(r'^(\d+)/clarifications/$', 'clarification_report', name='clarification_report'),
             )
