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

from django.core.urlresolvers import reverse
from model_mommy import mommy
from selenium.webdriver.support.wait import WebDriverWait

from core.test_utils import BaseSeleniumTestCase
from exmo2010.models import User, Monitoring, Organization, Task, Parameter, Score, MONITORING_RATE


class TaskListAjaxActionTestCase(BaseSeleniumTestCase):
    ''' Should update task status and allowed actions when action link clicked '''

    def setUp(self):
        # GIVEN expertB account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND MONITORING_RATE monitoring with organization, and open task
        self.monitoring = mommy.make(Monitoring, status=MONITORING_RATE)
        organization = mommy.make(Organization, name='org1', monitoring=self.monitoring)
        self.task = mommy.make(
            Task,
            organization=organization,
            user=expertB,
            status=Task.TASK_OPEN,
        )

        # AND parameter with only 'accessible' attribute
        parameter = mommy.make(
            Parameter,
            monitoring=self.monitoring,
            complete = False,
            accessible = True,
            topical = False,
            hypertext = False,
            document = False,
            image = False,
            npa = False
        )

        # AND score with filled values for all parameter attributes (complete score)
        score = mommy.make(Score, task=self.task, parameter=parameter, found=1, accessible=1)

        # AND i am logged in as expertB
        self.login('expertB', 'password')

    def test_open_action_status_update(self):
        # WHEN i open tasks_by_monitoring page
        self.get(reverse('exmo2010:tasks_by_monitoring', args=(self.monitoring.pk,)))
        td = '#task-status-%s' % self.task.pk
        # THEN current (TASK_OPEN) status_display should be displayed
        open_status_display = dict(Task.TASK_STATUS).get(Task.TASK_OPEN)
        self.assertEqual(self.find(td + ' .task_status_display').text, open_status_display)
        # AND 'close' action link should be visible
        self.wait_visible(td + ' .perms_close_task a')
        # AND 'open' and 'approve' action links should be hidden
        self.wait_visible(td + ' .perms_open_task a', False)
        self.wait_visible(td + ' .perms_approve_task a', False)
        # WHEN i click 'close' action link
        self.find(td + ' .perms_close_task a').click()
        # THEN 'open' action link should become visible
        self.wait_visible(td + ' .perms_open_task a')
        # AND 'close' action link should become hidden
        self.wait_visible(td + ' .perms_close_task a', False)
        # AND new (TASK_CLOSED) status_display should be displayed
        closed_status_display = dict(Task.TASK_STATUS).get(Task.TASK_CLOSED)
        self.assertEqual(self.find(td + ' .task_status_display').text, closed_status_display)
        # AND task should really change status to TASK_CLOSED in the database (no ObjectDoesNotExist exception raised)
        Task.objects.get(pk=self.task.pk, status=Task.TASK_CLOSED)
