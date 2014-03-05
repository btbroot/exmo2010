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
from django.conf.urls import *
from django.contrib.auth import views as auth_views
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView

from exmo2010.custom_registration.views import (activate_redirect, login_test_cookie, password_reset_confirm,
                                                password_reset_done, password_reset_redirect, register_test_cookie,
                                                resend_email)


urlpatterns = patterns('',
    url(r'^settings/$', 'accounts.views.settings', name='settings'),
    url(r'^activate/complete/$', TemplateView.as_view(template_name='registration/activation_complete.html'),
        name='registration_activation_complete'),
    # Activation keys get matched by \w+ instead of the more specific
    # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
    # that way it can return a sensible "invalid key" message instead of a
    # confusing 404.
    url(r'^activate/(?P<activation_key>\w+)/$', activate_redirect, name='registration_activate'),
    url(r'^register/$', register_test_cookie, name='registration_register'),
    url(r'^register/complete/$', TemplateView.as_view(
        template_name='registration/registration_complete.html',
        get_context_data=lambda: {'title': _('Registration (step 2 of 2)')}
        ), name='registration_complete'),
    url(r'^register/closed/$', TemplateView.as_view(template_name='registration/registration_closed.html'),
        name='registration_disallowed'),
    # Auth urls.
    url(r'^login/$', login_test_cookie, {'template_name': 'registration/login.html'},
        name='auth_login'),
    url(r'^resend_activation_email/$', resend_email, name='auth_resend_email'),
    url(r'^logout/$', auth_views.logout, {'next_page': reverse_lazy('exmo2010:index')},
        name='auth_logout'),
    url(r'^password/reset/$', password_reset_redirect,
        {'post_reset_redirect': reverse_lazy('exmo2010:auth_password_reset_done')},
        name='auth_password_reset'),
    url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        password_reset_confirm,
        name='auth_password_reset_confirm'),
    url(r'^password/reset/done/$', password_reset_done, name='auth_password_reset_done'),
)
