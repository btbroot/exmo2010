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
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy

from exmo2010.models import Monitoring, Organization, Parameter, Task, Score, INT


class SuperuserRatingOrgsVisibilityTestCase(TestCase):
    # exmo2010:monitoring_rating

    # Superuser should see all organizations on rating page

    def setUp(self):
        # GIVEN interaction monitoring
        self.monitoring = mommy.make(Monitoring, status=INT)
        # AND 2 organizations connected to monitoring
        organization1 = mommy.make(Organization, name='org1', monitoring=self.monitoring)
        organization2 = mommy.make(Organization, name='org2', monitoring=self.monitoring)
        # AND 2 approved tasks connected to organizations
        self.task1 = mommy.make(Task, organization=organization1, status=Task.TASK_APPROVED)
        self.task2 = mommy.make(Task, organization=organization2, status=Task.TASK_APPROVED)
        # AND parameter connected to monitoring
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        # AND 1 score for each task
        mommy.make(Score, task=self.task1, parameter=self.parameter)
        mommy.make(Score, task=self.task2, parameter=self.parameter)
        # AND superuser account
        User.objects.create_superuser('admin', 'admin@svobodainfo.org', 'password')
        # AND monitoring rating page url
        self.url = reverse('exmo2010:monitoring_rating', args=[self.monitoring.pk])
        # AND I am logged in as superuser
        self.client.login(username='admin', password='password')

    def test_rating_list(self):
        # WHEN I get rating page
        response = self.client.get(self.url)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND count of approved tasks should be 2
        self.assertEqual(len(response.context['rating_list']), 2)
