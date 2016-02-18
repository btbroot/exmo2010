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

from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy

from core.utils import UnicodeReader
from custom_comments.models import CommentExmo
from exmo2010.models import (Monitoring, Organization, Parameter, Task, Score, OrgUser)


class RepresentativesExportTestCase(TestCase):
    # exmo2010:representatives_export

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND there is 1 organization in monitoring
        org = mommy.make(Organization, monitoring=self.monitoring)
        # AND expert A account
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True
        # AND expert B with approved task in monitoring
        self.expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        self.expertB.profile.is_expertB = True
        task = mommy.make(Task, organization=org, user=self.expertB, status=Task.TASK_APPROVED)
        # AND parameter with score
        parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        score = mommy.make(Score, task=task, parameter=parameter)
        # AND org representative
        orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        orguser.groups.add(Group.objects.get(name=orguser.profile.organization_group))
        mommy.make(OrgUser, organization=org, userprofile=orguser.profile)
        # AND comment from orguser
        mommy.make(CommentExmo, object_pk=score.pk, user=orguser)
        # AND I am logged in as expert A
        self.client.login(username='expertA', password='password')

    def test_csv(self):
        # WHEN I get csv-file from response for current monitoring
        monitoring = Monitoring.objects.get(pk=self.monitoring.pk)
        url = reverse('exmo2010:representatives_export', args=[monitoring.pk])
        response = self.client.get(url)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND csv-file should be valid
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        csv = UnicodeReader(StringIO(response.content))
        organization = monitoring.organization_set.all()[0]
        user = organization.userprofile_set.all()[0]
        for row in csv:
            if row[0].startswith('#'):
                continue
            # AND length of row should be 10
            self.assertEqual(len(row), 10)
            # AND row 1 should contain user activation status
            self.assertEqual(int(row[0]), int(user.user.is_active))
            # AND row 2 should contain organization name
            self.assertEqual(row[1], organization.name)
            # AND row 3 should contain user first name
            self.assertEqual(row[2], user.user.first_name)
            # AND row 4 should contain user last name
            self.assertEqual(row[3], user.user.last_name)
            # AND row 5 should contain user e-mail
            self.assertEqual(row[4], user.user.email)
            # AND row 6 should contain user phone number
            self.assertEqual(row[5], user.phone or '')
            # AND row 7 should contain user job title
            self.assertEqual(row[6], user.position or '')
            # AND row 8 should contain count of comments
            self.assertEqual(int(row[7]), 1)
            # AND row 9 should contain date of user registration
            self.assertEqual(row[8], user.user.date_joined.date().isoformat())
            # AND row 10 should contain date of user last login
            self.assertEqual(row[9], user.user.last_login.date().isoformat())
