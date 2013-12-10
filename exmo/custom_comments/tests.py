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
from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy import mommy

from custom_comments.utils import comment_report
from exmo2010.models import *


class CommentReportTestCase(TestCase):
    # Scenario: Check comment report function

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        # AND organization connected to monitoring
        self.organization1 = mommy.make(Organization, name='org1', monitoring=self.monitoring)
        # AND two registered organizations representatives
        self.user1 = User.objects.create_user('user1')
        user_profile1 = self.user1.get_profile()
        user_profile1.organization.add(self.organization1)
        user_profile1.save()
        self.user2 = User.objects.create_user('user2')
        user_profile2 = self.user2.get_profile()
        user_profile2.organization.add(self.organization1)
        user_profile2.save()
        # AND organization without representatives
        self.organization2 = mommy.make(Organization, name='org2', monitoring=self.monitoring)

    def test_count_of_organizations_with_representatives(self):
        # WHEN comment report is generated for monitoring with two organizations
        report = comment_report(self.monitoring)
        # THEN count of organizations with representatives equals 1
        self.assertEqual(len(report['organizations_with_representatives']), 1)


class CommentGetQueryAccessTestCase(TestCase):
    # Scenario: should disallow to send get-query

    def test_anonymous_send_get_query(self):
        # WHEN anonymous user send GET-query
        url = reverse('comments-post-comment')
        response = self.client.get(url, follow=True)
        # THEN response status_code should be 405 (Method Not Allowed)
        self.assertEqual(response.status_code, 405)
