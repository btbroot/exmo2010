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


class ParameterEditAccessTestCase(TestCase):
    # SHOULD allow only expertA to edit parameter

    def setUp(self):
        self.client = Client()
        # GIVEN monitoring with organization, task and parameter
        self.monitoring = mommy.make(Monitoring)
        organization = mommy.make(Organization, monitoring=self.monitoring)
        task = mommy.make(Task, organization=organization)
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1, code=1, name='initial')

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
        org.profile.organization = [organization]

        self.url = reverse('exmo2010:parameter_manager', args=[task.pk, self.parameter.pk, 'update'])

    def test_anonymous_param_edit_get(self):
        # WHEN anonymous user gets parameter edit page
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
    def test_param_edit_get(self, username, expected_response_code):
        self.client.login(username=username, password='password')

        # WHEN user gets parameter edit page
        response = self.client.get(self.url)

        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand([
        ('user',),
        ('org',),
        ('expertB',),
    ])
    def test_forbid_unauthorized_param_edit_post(self, username):
        self.client.login(username=username, password='password')

        # WHEN unauthorized user forges and POSTs parameter edit form with changed weight, code and name
        self.client.post(self.url, dict(monitoring=self.monitoring.pk, code=2, weight=2, name='forged'))

        # THEN parameter does not get changed in the database
        initial_fields = {f: getattr(self.parameter, f) for f in 'weight code name'.split()}
        new_param_fields = Parameter.objects.values(*initial_fields).get(pk=self.parameter.pk)
        self.assertEqual(new_param_fields, initial_fields)
