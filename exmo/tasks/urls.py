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
from parameters.views import ParameterManagerView
from tasks.views import TaskManagerView
import reversion

urlpatterns = \
    patterns('tasks.views',
             url(r'^$', 'tasks'),
             url(r'^task/(?P<pk>\d+)_(?P<method>\w+)/$',
                 reversion.create_revision()(TaskManagerView.as_view()),
                 name='task_manager'),
             url(r'^taskexport/(\d+)/$', 'task_export', name='task_export'),
             url(r'^taskimport/(\d+)/$', 'task_import', name='task_import'),
             )

urlpatterns += \
    patterns('parameters.views',
             url(r'^task/(?P<task_id>\d+)/parameter/(?P<pk>\d+)_(?P<method>\w+)/$',
                 ParameterManagerView.as_view(),
                 name='parameter_manager'),
             url(r'^task/(\d+)/parameter/add/$', 'parameter_add', name='parameter_add'),
             )
