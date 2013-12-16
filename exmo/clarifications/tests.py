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

from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test import TestCase
from model_mommy import mommy

from exmo2010.models import (
    Monitoring, Organization, Score,
    Task, MONITORING_INTERACTION)


class ClarificationEmailNotifyTestCase(TestCase):
    # SHOULD send email notification when clarification is created

    def setUp(self):
        # GIVEN MONITORING_INTERACTION monitoring
        monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)

        # AND organization
        organization = mommy.make(Organization, monitoring=monitoring)

        # AND superuser with Email address
        User.objects.create_superuser('admin1', 'admin@ya.ru', 'password')
        # AND superuser without Email address
        User.objects.create_superuser('admin2', None, 'password')
        # AND 2 expert B
        expertB1 = User.objects.create_user('expertB1', 'expertB1@ya.ru', 'password')
        expertB1.profile.is_expertB = True
        expertB2 = User.objects.create_user('expertB2', 'expertB2@ya.ru', 'password')
        expertB2.profile.is_expertB = True
        # AND expert A
        expertA = User.objects.create_user('expertA', 'expertA@ya.ru', 'password')
        expertA.profile.is_expertA = True
        # AND organization representative
        org_user = User.objects.create_user('org', 'org@ya.ru', 'password')
        org_user.profile.organization = [organization]

        # AND task for expertB1
        task = mommy.make(Task, organization=organization, user=expertB1)

        # AND score fot this task
        self.score = mommy.make(Score, task=task, parameter__monitoring=monitoring)

        # AND i logged in as expertA
        self.client = Client()
        self.client.login(username='expertA', password='password')

        # NOTE: pop message about task assignment to expertB1
        # TODO: get rid of this automatic email on Task creation, move to the view
        mail.outbox.pop()

    def test_notification_on_create(self):
        url = reverse('exmo2010:clarification_create', args=[self.score.pk])

        # WHEN i post new claim
        response = self.client.post(url, data={'clarification-comment': 'asd'}, follow=True)

        # THEN response status_code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND there should be 2 email messages in the outbox
        self.assertEqual(len(mail.outbox), 2)

        # AND both notifiee should get the email
        self.assertEqual(set(tuple(m.to) for m in mail.outbox), set([('expertB1@ya.ru',), ('expertA@ya.ru',)]))


