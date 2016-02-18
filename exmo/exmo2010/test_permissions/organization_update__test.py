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

from exmo2010.models import Monitoring, Organization, OrgUser, ObserversGroup


class OrganizationEditAccessTestCase(TestCase):
    # exmo2010:organization_update

    # Should allow only expertA to edit organization

    def setUp(self):
        # GIVEN monitoring with organization
        self.monitoring = mommy.make(Monitoring)
        self.organization = mommy.make(
            Organization, monitoring=self.monitoring, url='1.ru', email='1@ya.ru', name='initial')

        # AND user without any permissions
        User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND superuser
        User.objects.create_superuser('admin', 'admin@svobodainfo.org', 'password')
        # AND expert B
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.groups.add(Group.objects.get(name=expertB.profile.expertB_group))
        # AND expert A
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.groups.add(Group.objects.get(name=expertA.profile.expertA_group))
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        mommy.make(OrgUser, organization=self.organization, userprofile=orguser.profile)
        # AND observer user
        observer = User.objects.create_user('observer', 'observer@svobodainfo.org', 'password')
        # AND observers group for monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=self.monitoring)
        obs_group.organizations = [self.organization]
        obs_group.users = [observer]

        self.url = reverse('exmo2010:organization_update', args=[self.monitoring.pk, self.organization.pk])

    def test_anonymous_org_edit_get(self):
        # WHEN anonymous user gets organization edit page
        response = self.client.get(self.url, follow=True)
        # THEN he is redirected to login page
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + self.url)

    @parameterized.expand([
        ('user', 403),
        ('orguser', 403),
        ('observer', 403),
        ('expertB', 403),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_organization_edit_get(self, username, expected_response_code):
        self.client.login(username=username, password='password')

        # WHEN user gets organization edit page
        response = self.client.get(self.url)

        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand([
        ('user',),
        ('orguser',),
        ('observer',),
        ('expertB',),
    ])
    def test_forbid_unauthorized_organization_edit_post(self, username):
        self.client.login(username=username, password='password')

        # WHEN unauthorized user forges and POSTs organization edit form with changed url, email and name
        self.client.post(self.url, {
            'org-monitoring': self.monitoring.pk,
            'org-url': '2.ru',
            'org-email': '2@ya.ru',
            'org-name': 'forged'})

        # THEN organization does not get changed in the database
        initial_fields = {f: getattr(self.organization, f) for f in 'url email name'.split()}
        new_org_fields = Organization.objects.values(*initial_fields).get(pk=self.organization.pk)
        self.assertEqual(new_org_fields, initial_fields)
