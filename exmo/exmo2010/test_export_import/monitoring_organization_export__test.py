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

from cStringIO import StringIO

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy

from core.utils import UnicodeReader
from exmo2010.models import (Monitoring, Organization)


class OrganizationExportTestCase(TestCase):
    # exmo2010:monitoring_organization_export

    # Organizations export response should contain properly generated csv-file content.

    def setUp(self):
        # GIVEN published monitoring with 1 organization
        monitoring = mommy.make(Monitoring)
        # AND organization with email, url and phone
        self.org = mommy.make(Organization, monitoring=monitoring,
                              email='org@test.com', url='http://org.ru', phone='1234567')
        # AND expert A account
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND organization export url
        self.url = reverse('exmo2010:monitoring_organization_export', args=[monitoring.pk])

    def test_organization_csv(self):
        # WHEN I am logged in as expert A
        self.client.login(username='expertA', password='password')
        # AND download csv
        hostname = 'test.host.com'
        response = self.client.get(self.url, HTTP_HOST=hostname)
        # THEN status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND file should be csv-file
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        csv = [line for line in UnicodeReader(StringIO(response.content))]
        # AND file should contain 3 lines (header, 1 string of content and license)
        self.assertEqual(len(csv), 3)
        for row in csv:
            if not row[0].startswith('#'):
                # AND length of content line should equal 6
                self.assertEqual(len(row), 6)
                org_data = [
                    self.org.name,
                    self.org.url,
                    self.org.email,
                    self.org.phone,
                    self.org.inv_code,
                    'http://' + hostname + reverse('exmo2010:auth_orguser') + '?code={}'.format(self.org.inv_code)
                ]
                # AND content should describe existing organization
                self.assertEqual(row, org_data)
