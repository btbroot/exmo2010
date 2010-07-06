from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
  #(r'^admin/(.*)', admin.site.root),
  (r'^admin/', include(admin.site.urls)),
  (r'^exmo2010/', include('exmo.exmo2010.urls')),
  (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'exmo2010/login.html'}),
  (r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'template_name': 'exmo2010/logged_out.html'}),
)

