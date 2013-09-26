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
#    along with this program.  If not, see <http://www.gnu.usr/licenses/>.
#

from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.utils.translation import ungettext
from model_mommy import mommy
from exmo2010.models import *
from monitorings.views import rating, _total_orgs_translate


class RatingTableSettingsTestCase(TestCase):
    # Scenario: User settings for Rating Table columns
    def setUp(self):
        # GIVEN User and UserProfile model instances
        self.client = Client()
        self.usr = User.objects.create_user('usr', 'usr@svobodainfo.org', 'password')
        # AND published monitoring
        monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        self.monitoring_id = monitoring.pk
        organization = mommy.make(Organization, monitoring=monitoring)
        task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)
        parameter = mommy.make(Parameter, monitoring=monitoring)
        score = mommy.make(Score, task=task, parameter=parameter)

    def test_rt_settings_exist(self):
        # WHEN User instance is created
        # THEN instance has settings fields with values that equal True
        self.assertEqual(self.usr.profile.rt_representatives, True)
        self.assertEqual(self.usr.profile.rt_comment_quantity, True)
        self.assertEqual(self.usr.profile.rt_initial_openness, True)
        self.assertEqual(self.usr.profile.rt_final_openness, True)
        self.assertEqual(self.usr.profile.rt_difference, True)

    def test_rt_settings_change(self):
        # WHEN User logging in
        self.client.login(username='usr', password='password')
        # AND changes settings via web-interface
        url = reverse('exmo2010:monitoring_rating', args=[self.monitoring_id])
        self.client.get(url, {'initial_openness': 'on'})
        # THEN changes are stored in user's profile
        self.assertEqual(self.usr.profile.rt_representatives, False)
        self.assertEqual(self.usr.profile.rt_comment_quantity, False)
        self.assertEqual(self.usr.profile.rt_final_openness, False)
        self.assertEqual(self.usr.profile.rt_difference, False)


class RatingTableValuesTestCase(TestCase):
    # Scenario: Output to Rating Table
    def setUp(self):
        # GIVEN published monitoring
        self.client = Client()
        self.monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        self.monitoring_id = self.monitoring.pk
        self.url = reverse('exmo2010:monitoring_rating', args=[self.monitoring_id])
        organization = mommy.make(Organization, monitoring=self.monitoring)
        self.task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring)
        score = mommy.make(Score, task=self.task, parameter=self.parameter)

    def test_rt_row_output(self):
        # WHEN user requests rating page
        response = self.client.get(self.url)
        o = response.context['object_list'][0]
        # THEN output data equals default values for organization
        self.assertEqual(o['place'], 1)
        self.assertEqual(o['task'], self.task)
        self.assertEqual(o['repr_len'], 0)
        self.assertEqual(o['active_repr_len'], 0)
        self.assertEqual(o['comments'], 0)
        self.assertEqual(o['openness_first'], -1)
        self.assertEqual(o['openness'], 0)
        self.assertEqual(o['openness_delta'], 1)

    def test_rt_average_output(self):
        # WHEN user requests rating page
        response = self.client.get(self.url)
        a = response.context['average']
        # THEN output average data equals expected values
        self.assertEqual(a['total_tasks'], 1)
        self.assertEqual(a['repr_len'], 0)
        self.assertEqual(a['active_repr_len'], 0)
        self.assertEqual(a['comments'], 0)
        self.assertEqual(a['openness_first'], -1)
        self.assertEqual(a['openness'], 0)
        self.assertEqual(a['openness_delta'], 1)

    def test_organizations_count(self):
        # WHEN function accepts monitoring and parameters data
        rating_list, avg = rating(self.monitoring, [self.parameter])
        text = _total_orgs_translate(avg, rating_list, '')
        # THEN expected text and organization count exist in returned text
        expected_text = ungettext(
        'Altogether, there is %(count)d organization in the monitoring cycle',
        'Altogether, there are %(count)d organizations in the monitoring cycle',
        avg['total_tasks']
        ) % {'count': 1}
        self.assertTrue(expected_text in text)

