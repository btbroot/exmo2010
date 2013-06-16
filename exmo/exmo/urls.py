# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
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
from django.conf.urls import *
from django.conf import settings
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.http import HttpResponsePermanentRedirect

from core import site as exmo
from core.views import TemplateView
admin.autodiscover()


urlpatterns = patterns('',
    url(r'^admin/settings/', include('livesettings.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^comments/', include('custom_comments.urls')),
    url(r'^$', lambda request: HttpResponsePermanentRedirect(
        reverse('exmo2010:index'))),
    url(r'^exmo2010/', include(exmo.urls)),
    url(r'^tagging_autocomplete/', include('tagging_autocomplete.urls')),
    url(r'^jsi18n/', 'django.views.i18n.javascript_catalog'),
    url(r'^admin_tools/', include('admin_tools.urls')),
    url(r'^license.txt$', TemplateView.as_view(template_name='license.txt', content_type='text/plain'), name='license'),
    url(r'^ckeditor/', include('ckeditor.urls')),
)

if 'debug_toolbar' in settings.INSTALLED_APPS:
    urlpatterns += (url(r'', include('debug_toolbar_user_panel.urls')),)
