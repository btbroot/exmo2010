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
from django.conf.urls.defaults import *
from django.conf import settings
from django.core.urlresolvers import reverse

urlpatterns = patterns('',
  url( r'^score/(\d+)_(\d+)/$', 'exmo2010.view.score.score_add', name='score_add'),
  url( r'^score/(\d+)_(\w+)/$', 'exmo2010.view.score.score_manager', name='score_manager'),
  url( r'^score/(\d+)/$', 'exmo2010.view.score.score_view', name='score_view'),
  url( r'^scores/(\d+)/(print|printfull)?$',
      'exmo2010.view.score.score_list_by_task', name='score_list_by_task'),
  url( r'^score/(\d+)/comment/add$', 'exmo2010.view.score.score_add_comment', name='score_add_comment'),


  url( r'^score/(\d+)/claim/add$', 'exmo2010.view.claim.claim_manager', name='claim_manager'),
  url( r'^monitoring/(\d+)/claims/$', 'exmo2010.view.claim.claim_report', name='claim_report'),


  url( r'^tasks/$', 'exmo2010.view.task.tasks' ),
  url( r'^tasks/task/(\d+)_(\w+)/$', 'exmo2010.view.task.task_manager', name='task_manager'),
  url( r'^monitoring/(\d+)/organization/(\d+)/task/(\d+)_(\w+)/$', 'exmo2010.view.task.task_manager', name='task_manager'),
  url( r'^tasks/taskimport/(\d+)/$', 'exmo2010.view.task.task_import', name='task_import'),
  url( r'^tasks/taskexport/(\d+)/$', 'exmo2010.view.task.task_export', name='task_export'),
  url( r'^monitoring/(\d+)/task/add/$', 'exmo2010.view.task.task_add', name='task_add'),
  url( r'^monitoring/(\d+)/organization/(\d+)/task/add/$', 'exmo2010.view.task.task_add', name='task_add'),
  url( r'^monitoring/(\d+)/tasks/$', 'exmo2010.view.task.tasks_by_monitoring', name='tasks_by_monitoring'),
  url( r'^monitoring/(\d+)/organization/(\d+)/tasks/$', 'exmo2010.view.task.tasks_by_monitoring_and_organization', name='tasks_by_monitoring_and_organization'),
  url( r'^monitoring/(\d+)/mass_assign_tasks/$', 'exmo2010.view.task.task_mass_assign_tasks', name='task_mass_assign_tasks'),


  url( r'^monitoring/(\d+)/organizations/$', 'exmo2010.view.organization.organization_list', name='organization_list'),
  url( r'^monitoring/(\d+)/organization/(\d+)_(\w+)/$', 'exmo2010.view.organization.organization_manager', name='organization_manager'),


  url( r'^tasks/task/(\d+)/parameter/(\d+)_(\w+)/$', 'exmo2010.view.parameter.parameter_manager', name='parameter_manager'),
  url( r'^tasks/task/(\d+)/parameter/add/$', 'exmo2010.view.parameter.parameter_add',name='parameter_add'),


  url( r'^monitorings/$', 'exmo2010.view.monitoring.monitoring_list', name='monitoring_list'),
  url( r'^monitoring/add/$', 'exmo2010.view.monitoring.monitoring_add', name='monitoring_add'),
  url( r'^monitoring/(\d+)_(\w+)/$', 'exmo2010.view.monitoring.monitoring_manager', name='monitoring_manager'),
  url( r'^monitoring/(\d+)/experts/$', 'exmo2010.view.monitoring.monitoring_by_experts', name='monitoring_by_experts'),
  url( r'^monitoring/(\d+)/comment_report/$', 'exmo2010.view.monitoring.monitoring_comment_report',name='monitoring_comment_report'),
  url( r'^monitoring/(\d+)/parameter_export/$', 'exmo2010.view.monitoring.monitoring_parameter_export', name='monitoring_parameter_export'),
  url( r'^monitoring/(\d+)/parameter_import/$', 'exmo2010.view.monitoring.monitoring_parameter_import', name='monitoring_parameter_import'),
  url( r'^monitoring/(\d+)/organization_export/$', 'exmo2010.view.monitoring.monitoring_organization_export', name='monitoring_organization_export'),
  url( r'^monitoring/(\d+)/organization_import/$', 'exmo2010.view.monitoring.monitoring_organization_import', name='monitoring_organization_import'),
  url( r'^monitoring/(\d+)/parameter_filter/$', 'exmo2010.view.monitoring.monitoring_parameter_filter', name='monitoring_parameter_filter'),
  url( r'^monitoring/(\d+)/parameter_found_report/$', 'exmo2010.view.monitoring.monitoring_parameter_found_report', name='monitoring_parameter_found_report'),
  url( r'^monitoring/(\d+)/rating/$', 'exmo2010.view.monitoring.monitoring_rating', name='monitoring_rating'),
  url( r'^monitoring/(\d+)/by_criteria_mass_export/$', 'exmo2010.view.monitoring.monitoring_by_criteria_mass_export', name='monitoring_by_criteria_mass_export'),

  url( r'^monitoring/(\d+)/answers_export/$', 'exmo2010.view.answers.answers_export', name='monitoring_answers_export'),
  url( r'^monitoring/(\d+)/add_questionnaire/$',
      'exmo2010.view.monitoring.add_questionnaire', name='add_questionnaire'),
  # AJAX-вьюха для получения кода div'а для одного вопроса (c полями).
  url( r'^get_qq/$', 'exmo2010.view.monitoring.get_qq', name='get_qq'),
  # AJAX-вьюха для получения кода div'а для одного вопроса (без полей).
  url( r'^get_qqt/$', 'exmo2010.view.monitoring.get_qqt', name='get_qqt'),


  url(r'^reports/gender/$', 'exmo2010.view.reports.gender_stats',
      name='gender_stats'),

  url(r'^reports/comment/(\d+)/$', 'exmo2010.view.reports.comment_list',
      name='comment_list'),
)


urlpatterns += patterns('',
  url(r'^accounts/profile','exmo2010.view.user.user_profile', name='user_profile'),
  url(r'^accounts/profile/(\d+)$','exmo2010.view.user.user_profile', name='user_profile'),
  url(r'^accounts/dashboard_reset$','exmo2010.view.user.user_reset_dashboard', name='user_reset_dashboard'),
)
