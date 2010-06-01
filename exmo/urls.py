from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
  #(r'^admin/(.*)', admin.site.root),
  (r'^admin/', include(admin.site.urls)),
  (r'^exmo2010/', include('exmo.exmo2010.urls')),
)

