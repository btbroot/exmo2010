# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import url, patterns, include
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.views.generic import RedirectView

admin.autodiscover()


handler500 = 'exmo2010.views.server_error'


urlpatterns = patterns('',
    url(r'^license.txt$', RedirectView.as_view(url=settings.STATIC_URL + 'license.txt')),
    url(r'^release.txt$', RedirectView.as_view(url=settings.STATIC_URL + 'release.txt')),
)

urlpatterns += i18n_patterns('',
    url(r'^admin/settings/', include('livesettings.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^jsi18n/', 'django.views.i18n.javascript_catalog'),
    url(r'^admin_tools/', include('admin_tools.urls')),
    url(r'^ckeditor/', include('ckeditor.urls')),
    url(r'^', include('exmo2010.urls', namespace='exmo2010', app_name='exmo2010')),
)


# Serve media files when DEBUG is True.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
