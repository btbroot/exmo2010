# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Foundation "Institute for Information Freedom Development"
# Copyright 2013 Al Nikolov
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
from django.test import TestCase
from django.test.client import Client
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from model_mommy import mommy
from nose_parameterized import parameterized

from exmo2010.models import *


class TestOrganizationsPage(TestCase):
    # Scenario: try to get organizations page by any users
    def setUp(self):
        self.client = Client()
        # GIVEN published monitoring
        self.monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        # AND organization for this monitoring
        self.organization = mommy.make(Organization, monitoring=self.monitoring)
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
        self.org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        profile = self.org.get_profile()
        profile.organization = [self.organization]

    def test_anonymous_organizations_page_access(self):
        url = reverse('exmo2010:organization_list', args=[self.monitoring.pk])
        # WHEN anonymous user get organizations page
        resp = self.client.get(url)
        # THEN redirect to login page
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, settings.LOGIN_URL + '?next=' + url)

    @parameterized.expand([
        ('user', 403),
        ('org', 403),
        ('expertB', 403),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_authenticated__user_organizations_page_access(self, username, response_code):
        url = reverse('exmo2010:organization_list', args=[self.monitoring.pk])
        # WHEN user get organizations page
        self.client.login(username=username, password='password')
        resp = self.client.get(url)
        # THEN only admin and expert A have access
        self.assertEqual(resp.status_code, response_code)


class OrganizationEditAccessTestCase(TestCase):
    # SHOULD allow only expertA to edit organization

    def setUp(self):
        self.client = Client()
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
        org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        org.profile.organization = [self.organization]

        self.url = reverse('exmo2010:organization_manager', args=[self.monitoring.pk, self.organization.pk, 'update'])

    def test_anonymous_org_edit_get(self):
        # WHEN anonymous user gets organization edit page
        response = self.client.get(self.url)
        # THEN he is redirected to login page
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + self.url)

    @parameterized.expand([
        ('user', 403),
        ('org', 403),
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
        ('org',),
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
