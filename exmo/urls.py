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
from django.contrib import admin
from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.core.urlresolvers import reverse
from django.views.generic.simple import direct_to_template
from exmo2010 import site as exmo
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^comments/', include('django.contrib.comments.urls')),
    url(r'^$', lambda request: HttpResponsePermanentRedirect(
        reverse('exmo2010:index'))),
    url(r'^exmo2010/', include(exmo.urls)),
    url(r'^tagging_autocomplete/', include('tagging_autocomplete.urls')),
    url(r'^jsi18n/', 'django.views.i18n.javascript_catalog'),
    url(r'^admin_tools/', include('admin_tools.urls')),
    url(r'^license.txt$', direct_to_template,
        {'template': 'license.txt', 'mimetype': 'text/plain'},
        name='license'),
)

if settings.DEBUG:
    urlpatterns += (url(r'', include('debug_toolbar_user_panel.urls')),)
