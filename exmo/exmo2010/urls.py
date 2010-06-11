from django.conf.urls.defaults import *
from django.contrib.auth.models import User
from exmo.exmo2010.models import Organization, Score, Task

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

  (
    r'^score/(\d+)/$',
    'exmo.exmo2010.views.score_detail'
  ),

  (
    r'^task/(\d+)/$',
    'exmo.exmo2010.views.score_list_by_task'
  ),

  (
    r'^tasks/$',
    'exmo.exmo2010.views.table',
    {
        'queryset':     Task.objects.all(),
        'paginate_by':  5,
        'headers':      (
                          ('', None),
                          ('Organization', 'organization__name'),
                          ('Expert', 'user__username'),
                          ('Open', 'open'),
                          ('Complete', None),
                        ),
    },
    'task_list',
  ),

  #(
    #r'^tasks/add/?$',
    #'django.views.generic.create_update.create_object',
    #{'model': Task},
    #'task_form'
  #),

)
