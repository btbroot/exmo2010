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
from datetime import datetime

from django.test import TestCase
from django.test.client import Client
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.utils.formats import get_format

from model_mommy import mommy
from nose_parameterized import parameterized

from exmo2010.models import Organization, Monitoring, MONITORING_PREPARE


class MonitoringEditAccessTestCase(TestCase):
    # SHOULD allow only expertA to edit monitoring

    def setUp(self):
        self.client = Client()
        # GIVEN monitoring with organization and openness_expression
        #openness_expression = mommy.make(OpennessExpression, openness_expression)
        self.monitoring = mommy.make(Monitoring, name='initial', status=MONITORING_PREPARE)
        organization = mommy.make(Organization, monitoring=self.monitoring)

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

        self.url = reverse('exmo2010:monitoring_manager', args=[self.monitoring.pk, 'update'])

    def test_anonymous_monitoring_edit_get(self):
        # WHEN anonymous user gets monitoring edit page
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
    def test_monitoring_edit_get(self, username, expected_response_code):
        self.client.login(username=username, password='password')

        # WHEN user gets monitoring edit page
        response = self.client.get(self.url)

        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand([
        ('user',),
        ('org',),
        ('expertB',),
    ])
    def test_forbid_unauthorized_monitoring_edit_post(self, username):
        self.client.login(username=username, password='password')

        input_format = get_format('DATE_INPUT_FORMATS')[0]
        now = datetime.now().strftime(input_format)

        # WHEN unauthorized user forges and POSTs monitoring edit form with changed name
        self.client.post(self.url, {
            'rate_date': now,
            'interact_date': now,
            'finishing_date': now,
            'publish_date': now,
            'openness_expression': 8,
            'status': MONITORING_PREPARE,
            'name': 'forged'})

        # THEN monitoring does not get changed in the database
        new_name = Monitoring.objects.get(pk=self.monitoring.pk).name
        self.assertEqual(self.monitoring.name, new_name)
