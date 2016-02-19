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
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy

from exmo2010.models import Monitoring, Organization, Parameter, Task, Score, OrgUser, INT


class OrgUserRatingAccessTestCase(TestCase):
    # exmo2010:monitoring_rating

    # Should allow org representatives to see only related orgs in unpublished ratings

    def setUp(self):
        # GIVEN INT monitoring with 2 organizations and parameter
        self.monitoring_related = mommy.make(Monitoring, status=INT)
        organization = mommy.make(Organization, monitoring=self.monitoring_related)
        organization_unrelated = mommy.make(Organization, monitoring=self.monitoring_related)
        parameter = mommy.make(Parameter, monitoring=self.monitoring_related, weight=1)
        # AND representative user for one organization
        user = User.objects.create_user('orguser', 'usr@svobodainfo.org', 'password')
        user.groups.add(Group.objects.get(name=user.profile.organization_group))
        mommy.make(OrgUser, organization=organization, userprofile=user.profile)
        # AND INT monitoring with organization, not connected to representative user and parameter
        self.monitoring_unrelated = mommy.make(Monitoring, status=INT)
        organization_unrelated2 = mommy.make(Organization, monitoring=self.monitoring_unrelated)
        parameter_unrelated = mommy.make(Parameter, monitoring=self.monitoring_unrelated, weight=1)
        # AND approved task for each organization
        self.task_related = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)
        task_unrelated = mommy.make(Task, organization=organization_unrelated, status=Task.TASK_APPROVED)
        task_unrelated2 = mommy.make(Task, organization=organization_unrelated2, status=Task.TASK_APPROVED)
        # AND score for each task
        mommy.make(Score, task=self.task_related, parameter=parameter)
        mommy.make(Score, task=task_unrelated, parameter=parameter)
        mommy.make(Score, task=task_unrelated2, parameter=parameter_unrelated)
        # AND I am logged in as orguser
        self.client.login(username='orguser', password='password')

    def test_forbid_org_access_to_unrelated_unpublished_rating(self):
        url = reverse('exmo2010:monitoring_rating', args=[self.monitoring_unrelated.pk])
        # WHEN I get unrelated unpublished rating page
        response = self.client.get(url)
        # THEN response status_code should be 403 (forbidden)
        self.assertEqual(response.status_code, 403)

    def test_allow_org_see_related_org_unpublished_rating(self):
        url = reverse('exmo2010:monitoring_rating', args=[self.monitoring_related.pk])
        # WHEN I get related unpublished rating page
        response = self.client.get(url)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        tasks = [task.pk for task in response.context['rating_list']]
        # AND I see only my own task in the list
        self.assertEqual(tasks, [self.task_related.pk])
