# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013 Foundation "Institute for Information Freedom Development"
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

from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from model_mommy import mommy

from exmo2010.models import Monitoring, Group, User, Organization, TaskHistory, Task, MONITORING_INTERACTION


class TaskAssignSideEffectsTestCase(TestCase):
    # Scenario: Should notify user and create TaskHistory on Task creation/assign

    def setUp(self):
        self.client = Client()
        # GIVEN INTERACTION monitoring without tasks
        self.monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        self.monitoring_id = self.monitoring.pk
        # AND there is 2 organizations in this monitoring
        self.organization1 = mommy.make(Organization, monitoring=self.monitoring)
        self.organization2 = mommy.make(Organization, monitoring=self.monitoring)
        # AND i am logged-in as expertA
        usr = User.objects.create_user('expA', 'usr@svobodainfo.org', 'password')
        usr.groups.add(Group.objects.get(name=usr.profile.expertA_group))
        self.client.login(username='expA', password='password')
        # AND there is 2 active expertsB
        self.expertB1 = mommy.make_recipe('exmo2010.active_user')
        self.expertB1.profile.is_expertB = True
        self.expertB2 = mommy.make_recipe('exmo2010.active_user')
        self.expertB2.profile.is_expertB = True

    def test_mass_assign_tasks(self):
        # WHEN I mass-asign Tasks for 2 organizations to 2 users
        url = reverse('exmo2010:task_mass_assign_tasks', args=[self.monitoring_id])
        self.client.post(
            url,
            {
                'organizations': [self.organization1.pk, self.organization2.pk],
                'users': [self.expertB1.pk, self.expertB2.pk]
            })

        # THEN there should be 2x2 Tasks for each user/org pair
        self.assertEqual(Task.objects.count(), 4)
        # AND Every Task should have corresponding TaskHistory
        self.assertEqual(TaskHistory.objects.count(), 4)
        # AND Every expertB should receive 2 Email notifications about her new assigned Tasks
        self.assertEqual(len(mail.outbox), 4)


    def test_add_single_task(self):
        # WHEN I create new task
        url = reverse('exmo2010:task_add', args=[self.monitoring_id])
        res = self.client.post(
            url,
            {
                'organization': self.organization1.pk,
                'user': self.expertB1.pk,
                'status': Task.TASK_OPEN
            })

        # THEN There should be one Task and one TaskHistory
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(TaskHistory.objects.count(), 1)
        # AND TaskHistory should have correct params for Task
        task = Task.objects.all()[0]
        history = TaskHistory.objects.all()[0]
        self.assertEqual(history.task_id, task.pk)
        self.assertEqual(history.user, task.user)
        self.assertEqual(history.status, task.organization.monitoring.status)
        # AND expertB should receive Email notification about her new assigned Task
        self.assertEqual(len(mail.outbox), 1)


