# Copyright 2010 Al Nikolov <root@root.spb.ru>, Helsinki, Finland
# Copyright 2010 Institute of Information Freedom Development, non-profit partnership, Saint-Petersburg, Russia
#
# This file is part of EXMO2010 software.
#
# EXMO2010 is NOT distributable. NOBODY is permitted to use it without a written permission from the
# above copyright holders.
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

