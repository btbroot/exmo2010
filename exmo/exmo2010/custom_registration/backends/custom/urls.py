# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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
from django.contrib.auth import views as auth_views
from django.core.urlresolvers import reverse
from django.utils.functional import lazy
from django.utils.translation import ugettext as _
from exmo2010.custom_registration.views import activate_redirect, login_test_cookie, password_reset_confirm
from exmo2010.custom_registration.views import password_reset_redirect, register_test_cookie, resend_email
from exmo2010.view.breadcrumbs import BreadcrumbsView


reverse_lazy = lambda name=None, *args : lazy(reverse, str)(name, args=args)


urlpatterns = patterns('',
    url(r'^activate/complete/$', BreadcrumbsView.as_view(
        template_name='registration/activation_complete.html',
        get_context_data=lambda: {'current_title': _('Activation complete')}
        ),
        name='registration_activation_complete'),
    # Activation keys get matched by \w+ instead of the more specific
    # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
    # that way it can return a sensible "invalid key" message instead of a
    # confusing 404.
    url(r'^activate/(?P<activation_key>\w+)/$',
        activate_redirect,
       {'backend': 'exmo2010.custom_registration.backends.custom.CustomBackend'},
       name='registration_activate'),
    url(r'^register/$',
        register_test_cookie,
       {'backend': 'exmo2010.custom_registration.backends.custom.CustomBackend'},
       name='registration_register'),
    url(r'^register/complete/$', BreadcrumbsView.as_view(
        template_name='registration/registration_complete.html',
        get_context_data=lambda: {'current_title': _('Registration complete')}
        ),
        name='registration_complete'),
    url(r'^register/closed/$', BreadcrumbsView.as_view(
        template_name='registration/registration_closed.html',
        get_context_data=lambda: {'current_title': _('Registration disallowed')}
        ),
        name='registration_disallowed'),
    # Auth urls.
    url(r'^login/$',
        login_test_cookie,
        {'template_name': 'registration/login.html'},
        name='auth_login'),
    url(r'^resend_activation_email/$',
        resend_email,
        name='auth_resend_email'),
    url(r'^logout/$',
        auth_views.logout,
        {'next_page': reverse_lazy('exmo2010:index')},
        name='auth_logout'),
    url(r'^password/reset/$',
        password_reset_redirect,
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
