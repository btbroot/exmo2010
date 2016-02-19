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

import json
import unittest
from cStringIO import StringIO

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy

from core.utils import UnicodeReader
from exmo2010.models import Monitoring, Organization, Task, Parameter, Score
from exmo2010.models.monitoring import PUB


class MonitoringExportApprovedTestCase(TestCase):
    # exmo2010:monitoring_export

    # Should export only approved tasks

    def setUp(self):
        # GIVEN published monitoring with 1 organization
        self.monitoring = mommy.make(Monitoring, status=PUB)
        organization = mommy.make(Organization, monitoring=self.monitoring, name='_ooo')
        # AND 2 experts B
        expertB_1 = User.objects.create_user('expertB_1', 'expertB_1@svobodainfo.org', 'password')
        expertB_1.profile.is_expertB = True
        expertB_2 = User.objects.create_user('expertB_2', 'expertB_2@svobodainfo.org', 'password')
        expertB_2.profile.is_expertB = True
        # AND approved task assigned to expertB_1
        approved_task = mommy.make(
            Task,
            organization=organization,
            user=expertB_1,
            status=Task.TASK_APPROVED,
        )
        # AND open task assigned to expertB_2
        open_task = mommy.make(
            Task,
            organization=organization,
            user=expertB_2,
            status=Task.TASK_OPEN,
        )
        # AND 1 parameter
        parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        # AND 1 score for each task
        mommy.make(Score, task=approved_task, parameter=parameter)
        mommy.make(Score, task=open_task, parameter=parameter)

    def test_approved_json(self):
        url = reverse('exmo2010:monitoring_export', args=[self.monitoring.pk])
        response = self.client.get(url + '?format=json')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается json
        self.assertEqual(response.get('content-type'), 'application/json')
        json_file = json.loads(response.content)
        self.assertEqual(len(json_file['monitoring']['tasks']), 1, json.dumps(json_file, indent=2))

    def test_approved_csv(self):
        url = reverse('exmo2010:monitoring_export', args=[self.monitoring.pk])
        response = self.client.get(url + '?format=csv')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается csv
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        csv = [line for line in UnicodeReader(StringIO(response.content))]
        # only header, 1 string of content and license
        self.assertEqual(len(csv), 3)
