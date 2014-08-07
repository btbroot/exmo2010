# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
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
from django.test import TestCase
from model_mommy import mommy
from nose_parameterized import parameterized

from exmo2010.models import (
    Monitoring, Organization, Score, Claim,
    ObserversGroup, Task, MONITORING_RATE)


class ClaimCreateAccessTestCase(TestCase):
    # exmo2010:claim_create

    # Should allow only expertA to create claim

    def setUp(self):
        # GIVEN organization in RATE monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_RATE)

        # AND user without any permissions
        User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND expert B
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND expert A
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.organization = [org]
        # AND observer user
        observer = User.objects.create_user('observer', 'observer@svobodainfo.org', 'password')
        # AND observers group for rate monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=org.monitoring)
        obs_group.organizations = [org]
        obs_group.users = [observer]

        # AND score for expertB task
        score = mommy.make(Score, task__organization=org, task__user=expertB)
        # AND claim in that score
        self.claim = mommy.make(Claim, score=score)

        self.url = reverse('exmo2010:claim_create', args=[score.pk])

    def test_allow_expertA_claim_creation(self):
        self.client.login(username='expertA', password='password')

        # WHEN expertA submits claim form
        response = self.client.post(self.url, {'claim-comment': 'lol'}, follow=True)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # THEN new claim should get created in the database (2 claim should exist)
        self.assertEqual(Claim.objects.count(), 2)

    @parameterized.expand([
        ('user',),
        ('org',),
        ('observer',),
        ('expertB',),
    ])
    def test_forbid_unauthorized_claim_creation(self, username):
        self.client.login(username=username, password='password')

        # WHEN unauthorized user forges and POSTs claim form
        self.client.post(self.url, {'claim-comment': 'lol'})

        # THEN claim should not get created in the database (only one claim exist)
        self.assertEqual(Claim.objects.count(), 1)


class ClaimAnswerAccessTestCase(TestCase):
    # exmo2010:claim_answer

    # Should allow only expertB to answer claim

    def setUp(self):
        # GIVEN organization in RATE monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_RATE)

        # AND user without any permissions
        User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND expert B
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND expert A
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.organization = [org]
        # AND observer user
        observer = User.objects.create_user('observer', 'observer@svobodainfo.org', 'password')
        # AND observers group for rate monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=org.monitoring)
        obs_group.organizations = [org]
        obs_group.users = [observer]

        # AND score for expertB task
        score = mommy.make(Score, task__organization=org, task__user=expertB)
        # AND claim in that score
        self.claim = mommy.make(Claim, score=score)

        self.url = reverse('exmo2010:claim_answer', args=[self.claim.pk])
        post_field = '%s-answer' % self.claim.answer_form().prefix
        self.answer_data = {post_field: 'lol'}

    @parameterized.expand([
        ('user',),
        ('org',),
        ('observer',),
        ('expertA',),
    ])
    def test_forbid_unauthorized_claim_answer(self, username):
        self.client.login(username=username, password='password')

        # WHEN unauthorized user forges and POSTs claim form with answer to existing claim
        self.client.post(self.url, self.answer_data)

        # THEN claim answer should not change in the database
        self.assertEqual(Claim.objects.get(pk=self.claim.pk).answer, '')

    def test_allow_expertB_claim_answer(self):
        self.client.login(username='expertB', password='password')

        # WHEN expertB submits claim form with answer to existing claim
        response = self.client.post(self.url, self.answer_data, follow=True)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # THEN claim answer should change in the database
        self.assertEqual(Claim.objects.get(pk=self.claim.pk).answer, u'<p>lol</p>')


class ClaimDeleteAccessTestCase(TestCase):
    # exmo2010:claim_delete

    # Should allow only expertA to delete claim

    def setUp(self):
        # GIVEN organization in RATE monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_RATE)

        # AND user without any permissions
        User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND expert B
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND expert A
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.organization = [org]
        # AND observer user
        observer = User.objects.create_user('observer', 'observer@svobodainfo.org', 'password')
        # AND observers group for rate monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=org.monitoring)
        obs_group.organizations = [org]
        obs_group.users = [observer]

        # AND score for expertB task
        self.score = mommy.make(Score, task__organization=org, task__user=expertB)
        # AND claim in that score
        self.claim = mommy.make(Claim, score=self.score)

        self.url = reverse('exmo2010:claim_delete')

    @parameterized.expand([
        ('user',),
        ('org',),
        ('observer',),
        ('expertB',),
    ])
    def test_forbid_unauthorized_claim_deleteion(self, username):
        self.client.login(username=username, password='password')

        # WHEN unauthorized user forges and POSTs claim deletion form
        self.client.post(self.url, {'pk': self.claim.pk}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # THEN claim answer should not get deleted from the database
        self.assertEqual(Claim.objects.count(), 1)

    def test_allow_expertA_claim_delete(self):
        self.client.login(username='expertA', password='password')

        # WHEN expertA submits claim deletion form
        response = self.client.post(self.url, {'pk': self.claim.pk}, HTTP_X_REQUESTED_WITH='XMLHttpRequest', follow=True)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # THEN claim answer should get deleted from the database
        self.assertEqual(Claim.objects.count(), 0)


class ClaimCreatedEmailNotifyTestCase(TestCase):
    # exmo2010:claim_create

    # Should send email notification to expert A and B when claim is created

    def setUp(self):
        # GIVEN MONITORING_RATE monitoring
        monitoring = mommy.make(Monitoring, status=MONITORING_RATE)

        # AND organization
        org = mommy.make(Organization, monitoring=monitoring)

        # AND superuser with Email address
        User.objects.create_superuser('admin1', 'admin@ya.ru', 'password')
        # AND superuser without Email address
        User.objects.create_superuser('admin2', None, 'password')
        # AND expert B with task
        expertB1 = User.objects.create_user('expertB1', 'expertB1@ya.ru', 'password')
        expertB1.profile.is_expertB = True
        task = mommy.make(Task, organization=org, user=expertB1)
        # AND free expert B without task
        expertB_free = User.objects.create_user('expertB2', 'expertB2@ya.ru', 'password')
        expertB_free.profile.is_expertB = True
        # AND expert A
        expertA = User.objects.create_user('expertA', 'expertA@ya.ru', 'password')
        expertA.profile.is_expertA = True
        # AND organization representative
        org_user = User.objects.create_user('org', 'org@ya.ru', 'password')
        org_user.profile.organization = [org]

        # AND score
        self.score = mommy.make(Score, task=task, parameter__monitoring=monitoring)

        # AND i logged in as expertA
        self.client.login(username='expertA', password='password')

        # NOTE: pop message about task assignment to expertB1
        # TODO: get rid of this automatic email on Task creation, move to the view
        mail.outbox.pop()

    def test_notification_on_create(self):
        url = reverse('exmo2010:claim_create', args=[self.score.pk])

        # WHEN i post new claim
        response = self.client.post(url, data={'claim-comment': 'asd'}, follow=True)

        # THEN response status_code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND there should be 2 email messages in the outbox
        self.assertEqual(len(mail.outbox), 2)

        # AND both notifiee should get the email
        self.assertEqual(set(tuple(m.to) for m in mail.outbox), set([('expertB1@ya.ru',), ('expertA@ya.ru',)]))


class ClaimDeletedEmailNotifyTestCase(TestCase):
    # exmo2010:claim_delete

    # Should send email notification to expert A and B when claim is deleted

    def setUp(self):
        # GIVEN MONITORING_RATE monitoring
        monitoring = mommy.make(Monitoring, status=MONITORING_RATE)

        # AND organization
        org = mommy.make(Organization, monitoring=monitoring)

        # AND superuser with Email address
        User.objects.create_superuser('admin1', 'admin@ya.ru', 'password')
        # AND superuser without Email address
        User.objects.create_superuser('admin2', None, 'password')
        # AND expert B with task
        expertB1 = User.objects.create_user('expertB1', 'expertB1@ya.ru', 'password')
        expertB1.profile.is_expertB = True
        task = mommy.make(Task, organization=org, user=expertB1)
        # AND free expert B without task
        expertB_free = User.objects.create_user('expertB2', 'expertB2@ya.ru', 'password')
        expertB_free.profile.is_expertB = True
        # AND expert A
        expertA = User.objects.create_user('expertA', 'expertA@ya.ru', 'password')
        expertA.profile.is_expertA = True
        # AND organization representative
        org_user = User.objects.create_user('org', 'org@ya.ru', 'password')
        org_user.profile.organization = [org]

        # AND score with existing claim
        self.score = mommy.make(Score, task=task, parameter__monitoring=monitoring)
        self.claim = mommy.make(Claim, score=self.score, creator=expertA, comment='asd', addressee=expertB1)

        # AND i logged in as expertA
        self.client.login(username='expertA', password='password')

        # NOTE: pop message about task assignment to expertB1
        # TODO: get rid of this automatic email on Task creation, move to the view
        mail.outbox.pop()

    def test_notification_on_delete(self):
        url = reverse('exmo2010:claim_delete')

        # WHEN i post claim deletion ajax request
        response = self.client.post(url, data={'pk': self.claim.pk}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # THEN response status_code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND there should be 2 email messages in the outbox
        self.assertEqual(len(mail.outbox), 2)

        # AND both notifiee should get the email
        self.assertEqual(set(tuple(m.to) for m in mail.outbox), set([('expertB1@ya.ru',), ('expertA@ya.ru',)]))
