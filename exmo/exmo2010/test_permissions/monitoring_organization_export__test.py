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
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from mock import MagicMock, Mock
from model_mommy import mommy
from nose_parameterized import parameterized

from ..views.export_import import monitoring_organization_export
from core.test_utils import OptimizedTestCase
from exmo2010.models import (Monitoring, ObserversGroup, OrgUser, Organization)


class OrganizationExportAccessTestCase(OptimizedTestCase):
    # exmo2010:monitoring_organization_export

    # Should allow experts A and superusers download csv-file.
    # Should redirect anonymous to login page.
    # Should forbid all other users to download csv-file.

    @classmethod
    def setUpClass(cls):
        super(OrganizationExportAccessTestCase, cls).setUpClass()

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
        # AND url
        cls.url = reverse('exmo2010:monitoring_organization_export', args=[cls.monitoring.pk])

    @parameterized.expand(zip(['admin', 'expertA']))
    def test_allow_csv(self, username, *args):
        # WHEN privileged user download file
        request = Mock(user=self.users[username], method='GET')
        response = monitoring_organization_export(request, self.monitoring.pk)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

    @parameterized.expand(zip(['expertB', 'orguser', 'translator', 'observer', 'user']))
    def test_forbid_csv(self, username, *args):
        # WHEN authenticated user without permissions download file
        request = Mock(user=self.users[username], method='GET')
        # THEN response should raise PermissionDenied exception
        self.assertRaises(PermissionDenied, monitoring_organization_export, request, self.monitoring.pk)

    def test_redirect_anonymous(self):
        # WHEN anonymous user download file
        request = MagicMock(user=self.users['anonymous'], method='GET')
        request.get_full_path.return_value = self.url
        response = monitoring_organization_export(request, self.monitoring.pk)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to login page
        self.assertEqual(response['Location'], '{}?next={}'.format(settings.LOGIN_URL, self.url))
