# This file is part of EXMO2010 software.
# Copyright 2010 Al Nikolov
# Copyright 2010 Institute for Information Freedom Development
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
from django.contrib.auth.models import User
from django.conf import settings

urlpatterns = patterns('',
  (r'^admin/doc/', include('django.contrib.admindocs.urls')),

  (
    r'^parameters/(\d+)/$',
    'exmo.exmo2010.views.parameter_by_organization_list'
  ),

  (
    r'^score/(\d+)_(\d+)/$',
    'exmo.exmo2010.views.score_detail'
  ),

  (
    r'^score/(\d+)_(\w+)/$',
    'exmo.exmo2010.views.score_detail_direct'
  ),

  ( r'^scores/(\d+)/(print|printfull)?$', 'exmo.exmo2010.views.score_list_by_task' ),

  ( r'^tasks/$', 'exmo.exmo2010.views.tasks' ),

  ( r'^tasks/task/(\d+)_(\w+)/$', 'exmo.exmo2010.views.task_manager' ),

  ( r'^tasks/task/(\d+)/parameter/(\d+)_(\w+)/$', 'exmo.exmo2010.views.parameter_manager' ),

  ( r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_DOC_ROOT} ),

  (r'^api/organization/$', 'exmo.exmo2010.api.organization_lookup'),

  ( r'^tasks/taskimport/(\d+)/$', 'exmo.exmo2010.views.task_import' ),
  ( r'^tasks/taskexport/(\d+)/$', 'exmo.exmo2010.views.task_export' ),
  ( r'^score/(\d+)/comment/add$', 'exmo.exmo2010.views.add_comment' ),
  ( r'^score/(\d+)/claim/add$', 'exmo.exmo2010.view.claim.claim_manager' ),

  ( r'^monitorings/$', 'exmo.exmo2010.views.monitoring_list' ),
  ( r'^monitoring/(\d+)_(\w+)/$', 'exmo.exmo2010.views.monitoring_manager' ),
  ( r'^monitoring/(\d+)/organizations/$', 'exmo.exmo2010.views.organization_list' ),
  ( r'^monitoring/(\d+)/tasks/$', 'exmo.exmo2010.views.tasks_by_monitoring' ),
  ( r'^monitoring/(\d+)/task/add/$', 'exmo.exmo2010.views.task_add' ),
  ( r'^monitoring/(\d+)/experts/$', 'exmo.exmo2010.views.monitoring_by_experts' ),
  ( r'^monitoring/(\d+)/parameter_filter/$', 'exmo.exmo2010.views.monitoring_parameter_filter' ),
  ( r'^monitoring/(\d+)/parameter_found_report/$', 'exmo.exmo2010.views.monitoring_parameter_found_report' ),
  ( r'^monitoring/(\d+)/organization/(\d+)_(\w+)/$', 'exmo.exmo2010.views.organization_manager' ),
  ( r'^monitoring/(\d+)/organization/(\d+)/tasks/$', 'exmo.exmo2010.views.tasks_by_monitoring_and_organization' ),
  ( r'^monitoring/(\d+)/organization/(\d+)/task/(\d+)_(\w+)/$', 'exmo.exmo2010.views.task_manager' ),
  ( r'^monitoring/(\d+)/organization/(\d+)/task/add/$', 'exmo.exmo2010.views.task_add' ),

  ( r'^monitoring/(\d+)/rating/$', 'exmo.exmo2010.views.rating' ),
  ( r'^monitoring/(\d+)/by_criteria_mass_export/$', 'exmo.exmo2010.views.monitoring_by_criteria_mass_export' ),
  ( r'^monitoring/(\d+)/mass_assign_tasks/$', 'exmo.exmo2010.views.mass_assign_tasks' ),
)
