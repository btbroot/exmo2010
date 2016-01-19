# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2016 IRSI LTD
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

from __future__ import unicode_literals

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from mock import MagicMock, Mock
from model_mommy import mommy
from nose_parameterized import parameterized

from monitorings.views import monitorings_list
from core.test_utils import OptimizedTestCase
from exmo2010.models import Monitoring, ObserversGroup, OrgUser, User, AnonymousUser, Organization


class MonitoringsAccessTestCase(OptimizedTestCase):
    # exmo2010:monitorings_list

    # Should always redirect anonymous to login page.
    # Should forbid get requests for non-experts.
    # Should forbid get requests with incorrect parameters for experts.
    # Should allow get requests with correct parameters for experts.

    @classmethod
    def setUpClass(cls):
        super(MonitoringsAccessTestCase, cls).setUpClass()

        cls.users = {}
        # GIVEN monitoring with organization
        cls.monitoring = mommy.make(Monitoring)
        organization = mommy.make(Organization, monitoring=cls.monitoring)
        # AND anonymous user
        cls.users['anonymous'] = AnonymousUser()
        # AND user without any permissions
        cls.users['user'] = User.objects.create_user('user', 'usr@svobodainfo.org', 'password')
        # AND superuser
        cls.users['admin'] = User.objects.create_superuser('admin', 'usr@svobodainfo.org', 'password')
        # AND expert B
        expertB = User.objects.create_user('expertB', 'usr@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        cls.users['expertB'] = expertB
        # AND expert A
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        cls.users['expertA'] = expertA
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'usr@svobodainfo.org', 'password')
        mommy.make(OrgUser, organization=organization, userprofile=orguser.profile)
        cls.users['orguser'] = orguser
        # AND translator
        translator = User.objects.create_user('translator', 'usr@svobodainfo.org', 'password')
        translator.profile.is_translator = True
        cls.users['translator'] = translator
        # AND observer user
        observer = User.objects.create_user('observer', 'usr@svobodainfo.org', 'password')
        # AND observers group for monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=cls.monitoring)
        obs_group.organizations = [organization]
        obs_group.users = [observer]
        cls.users['observer'] = observer
        # AND page url
        cls.url = reverse('exmo2010:monitorings_list')

    @parameterized.expand(zip(['GET', 'POST']))
    def test_redirect_anonymous(self, method, *args):
        # WHEN anonymous user send request to monitorings page
        request = MagicMock(user=self.users['anonymous'], method=method)
        request.get_full_path.return_value = self.url
        response = monitorings_list(request)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to login page
        self.assertEqual(response['Location'], '{}?next={}'.format(settings.LOGIN_URL, self.url))

    @parameterized.expand(zip(['orguser', 'translator', 'observer', 'user']))
    def test_forbid_get(self, username, *args):
        # WHEN authenticated user get monitorings page
        request = Mock(user=self.users[username], method='GET')
        # THEN response should raise PermissionDenied exception
        self.assertRaises(PermissionDenied, monitorings_list, request)

    @parameterized.expand(zip(['admin', 'expertA', 'expertB']))
    def test_allow_get(self, username, *args):
        # WHEN admin or any expert get monitorings page
        request = MagicMock(user=self.users[username], method='GET')
        response = monitorings_list(request)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

    @parameterized.expand(zip(['unpublished', 'published']))
    def test_allow_get_with_params(self, param, *args):
        # WHEN admin or any expert get monitorings page
        request = MagicMock(user=self.users['expertA'], method='GET')
        response = monitorings_list(request, param)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

    @parameterized.expand(zip(['orguser', 'translator', 'observer', 'user']))
    def test_forbid_post(self, username, *args):
        # WHEN authenticated user changes columns visibility settings on monitorings page
        data = {'mon_evaluation_start': True,
                'mon_interact_start': False,
                'mon_interact_end': True,
                'mon_publish_date': False,
                'columns_picker_submit': True}
        request = Mock(user=self.users[username], method='POST', POST=data)
        # THEN response should raise PermissionDenied exception
        self.assertRaises(PermissionDenied, monitorings_list, request)

    @parameterized.expand(zip(['admin', 'expertA', 'expertB']))
    def test_allow_post(self, username, *args):
        # WHEN admin or any expert changes columns visibility settings on monitorings page
        data = {'mon_evaluation_start': True,
                'mon_interact_start': False,
                'mon_interact_end': True,
                'mon_publish_date': False,
                'columns_picker_submit': True}
        request = MagicMock(user=self.users[username], method='POST', POST=data)
        request.get_full_path.return_value = self.url
        response = monitorings_list(request)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
