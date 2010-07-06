# Copyright 2010 Al Nikolov <root@root.spb.ru>, Helsinki, Finland
# Copyright 2010 Institute of Information Freedom Development, non-profit partnership, Saint-Petersburg, Russia
#
# This file is part of EXMO2010 software.
#
# EXMO2010 is NOT distributable. NOBODY is permitted to use it without a written permission from the
# above copyright holders.
from django.conf.urls.defaults import *
from django.contrib.auth.models import User
from exmo.exmo2010.models import Organization, Score, Task

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
    r'^score/(\d+)/$',
    'exmo.exmo2010.views.score_detail_direct'
  ),

  (
    r'^scores/(\d+)/$',
    'exmo.exmo2010.views.score_list_by_task'
  ),

  ( r'^tasks/$', 'exmo.exmo2010.views.tasks' ),

  ( r'^tasks/task/(\d+)_(\w+)/$', 'exmo.exmo2010.views.task_manager' ),
)
