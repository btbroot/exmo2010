# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2016 IRSI LTD
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
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy
from nose_parameterized import parameterized

from exmo2010.models import Organization, MONITORING_INTERACTION, OrgUser


class ManageOrgsPageAccessTestCase(TestCase):
    # exmo2010:manage_orgs

    # Scenario: try to get organizations page by any users
    def setUp(self):
        # GIVEN organization in INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION)
        # AND user without any permissions
        self.user = User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND superuser
        self.admin = User.objects.create_superuser('admin', 'admin@svobodainfo.org', 'password')
        # AND expert B
        self.expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        self.expertB.groups.add(Group.objects.get(name=self.expertB.profile.expertB_group))
        # AND expert A
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.groups.add(Group.objects.get(name=self.expertA.profile.expertA_group))
        # AND organizations representative
        self.orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        mommy.make(OrgUser, organization=org, userprofile=self.orguser.get_profile())

        self.url = reverse('exmo2010:manage_orgs', args=[org.monitoring.pk])

    def test_anonymous_organizations_page_access(self):
        # WHEN anonymous user get organizations page
        resp = self.client.get(self.url, follow=True)
        # THEN redirect to login page
        self.assertRedirects(resp, settings.LOGIN_URL + '?next=' + self.url)

    @parameterized.expand([
        ('user', 403),
        ('orguser', 403),
        ('expertB', 403),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_authenticated__user_organizations_page_access(self, username, response_code):
        # WHEN user get organizations page
        self.client.login(username=username, password='password')
        resp = self.client.get(self.url)
        # THEN only admin and expert A have access
        self.assertEqual(resp.status_code, response_code)
