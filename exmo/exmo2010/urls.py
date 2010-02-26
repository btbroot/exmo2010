from django.conf.urls.defaults import *
from django.contrib.auth.models import User
from exmo.exmo2010.models import Organization

urlpatterns = patterns('',
  (r'^admin/doc/', include('django.contrib.admindocs.urls')),
  #(
    #r'^$',
    #'django.views.generic.simple.direct_to_template',
    #{'template': 'exmo2010/index.html'},
    #'index'
  #),

  (
    r'^organizations/$',
    'django.views.generic.list_detail.object_list',
    {'queryset': Organization.objects.all()},
    'organization_list'
  ),

  (
    r'^parameters/(\d+)/$',
    'exmo.exmo2010.views.parameter_by_organization_list'
  ),

  (
    r'^score/(\d+)/(\d+)/$',
    'exmo.exmo2010.views.score_by_organization_parameter_detail'
  ),

  #(
    #r'^tasks/add/?$',
    #'django.views.generic.create_update.create_object',
    #{'model': Task},
    #'task_form'
  #),

)
