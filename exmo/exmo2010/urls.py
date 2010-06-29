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

  ( r'^tasks/$', 'exmo.exmo2010.views.tasks'),
  (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'exmo2010/login.html'}),
  (r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'template_name': 'exmo2010/logged_out.html'}),
)
