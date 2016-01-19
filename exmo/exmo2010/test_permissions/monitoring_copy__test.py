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

import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from django.utils.formats import get_format
from django.utils.translation import get_language
from model_mommy import mommy
from nose_parameterized import parameterized

from exmo2010.models import Monitoring, OrgUser, Organization
from exmo2010.models.monitoring import PRE


class MonitoringCopyAccessTestCase(TestCase):
    # exmo2010:monitoring_copy

    # TODO: move this testcase into *permissions* tests directory

    # Should allow only expertA to copy monitoring

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND organization
        organization = mommy.make(Organization, monitoring=self.monitoring)
        # AND superuser account
        User.objects.create_superuser('admin', 'usr@svobodainfo.org', 'password')
        # AND expert A account
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND expert B account
        expertB = User.objects.create_user('expertB', 'usr@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'usr@svobodainfo.org', 'password')
        mommy.make(OrgUser, organization=organization, userprofile=orguser.profile)
        # AND user without any permissions
        User.objects.create_user('user', 'usr@svobodainfo.org', 'password')
        # AND monitoring copy page url
        self.url = reverse('exmo2010:monitoring_copy', args=[self.monitoring.pk])

    def test_anonymous_monitoring_copy_get(self):
        # WHEN anonymous user gets monitoring copy page
        response = self.client.get(self.url, follow=True)
        # THEN he is redirected to login page
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + self.url)

    @parameterized.expand([
        ('user', 403),
        ('orguser', 403),
        ('expertB', 403),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_monitoring_copy_get(self, username, expected_response_code):
        # WHEN I am logged in
        self.client.login(username=username, password='password')
        # AND I get monitoring copy page
        response = self.client.get(self.url)
        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand([
        ('user',),
        ('orguser',),
        ('expertB',),
    ])
    def test_forbid_unauthorized_monitoring_copy_post(self, username):
        # WHEN I am logged in
        self.client.login(username=username, password='password')

        now = datetime.datetime.now().strftime(get_format('DATE_INPUT_FORMATS')[0])

        # AND I forge and POST monitoring copy form
        self.client.post(self.url, {
            'name_%s' % get_language(): 'monitoring name',
            'status': PRE,
            'openness_expression': 8,
            'donors': ['all'],
            'rate_date': now,
            'interact_date': now,
            'finishing_date': now,
            'publish_date': now,
        })
        # THEN monitoring copy does not get created in the database
        self.assertEqual(1, Monitoring.objects.all().count())
