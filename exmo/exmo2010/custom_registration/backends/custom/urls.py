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

"""
URLconf for registration and activation, using django-registration's
default backend.

If the default behavior of these views is acceptable to you, simply
use a line like this in your root URLconf to set up the default URLs
for registration::

    (r'^accounts/', include('registration.backends.default.urls')),

This will also automatically set up the views in
``django.contrib.auth`` at sensible default locations.

If you'd like to customize the behavior (e.g., by passing extra
arguments to the various views) or split up the URLs, feel free to set
up your own URL patterns for these views instead.

"""


from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.core.urlresolvers import reverse
from django.utils.functional import lazy
from django.contrib.auth import views as auth_views
from registration.views import activate, register
from exmo2010.custom_registration.views import password_reset_confirm
from exmo2010.custom_registration.views import reg_finish

reverse_lazy = lambda name=None, *args : lazy(reverse, str)(name, args=args)

urlpatterns = patterns('',
    url(r'^activate/complete/$',
       direct_to_template,
       {'template': 'registration/activation_complete.html'},
       name='registration_activation_complete'),
    # Activation keys get matched by \w+ instead of the more specific
    # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
    # that way it can return a sensible "invalid key" message instead of a
    # confusing 404.
    url(r'^activate/(?P<activation_key>\w+)/$',
       activate,
       {'backend': 'exmo2010.custom_registration.backends.custom.CustomBackend'},
       name='registration_activate'),
    url(r'^register/$',
       register,
       {'backend': 'exmo2010.custom_registration.backends.custom.CustomBackend'},
       name='registration_register'),
    url(r'^register/complete/$',
       direct_to_template,
       {'template': 'registration/registration_complete.html'},
       name='registration_complete'),
    url(r'^register/closed/$',
       direct_to_template,
       {'template': 'registration/registration_closed.html'},
       name='registration_disallowed'),
    url(r'^register/finish/$',
        reg_finish,
        name='registration_finish'),
    # Auth urls.
    url(r'^login/$',
        auth_views.login,
            {'template_name': 'registration/login.html'},
        name='auth_login'),
    url(r'^logout/$',
        auth_views.logout,
            {'template_name': 'registration/logout.html'},
        name='auth_logout'),
    url(r'^password/reset/$',
        auth_views.password_reset,
        {'post_reset_redirect':
             reverse_lazy('exmo2010:auth_password_reset_done')},
        name='auth_password_reset'),
    url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        password_reset_confirm,
        name='auth_password_reset_confirm'),
    url(r'^password/reset/done/$',
        auth_views.password_reset_done,
        name='auth_password_reset_done'),
)
