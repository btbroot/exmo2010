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
import json
import time

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from django.utils.crypto import salted_hmac
from django.utils.translation import ugettext as _
from model_mommy import mommy
from nose_parameterized import parameterized

from exmo2010.models import *
from scores.forms import ScoreFormWithComment


class ScoreAddccessTestCase(TestCase):
    # only expertB assigned to score's task SHOULD be allowed to create score

    def setUp(self):
        self.client = Client()
        # GIVEN monitoring with organization and parameter
        monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        organization = mommy.make(Organization, monitoring=monitoring)
        self.parameter = mommy.make(Parameter, monitoring=monitoring)

        # AND user without any permissions
        User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND superuser
        User.objects.create_superuser('admin', 'admin@svobodainfo.org', 'password')
        # AND expert B
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.groups.add(Group.objects.get(name=expertB.profile.expertB_group))
        # AND expert A
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.groups.add(Group.objects.get(name=expertA.profile.expertA_group))
        # AND organization representative
        org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        org.profile.organization = [organization]

        # AND score with task assigned to expertB
        self.task = mommy.make(Task, organization=organization, user=expertB)

        self.url = reverse('exmo2010:score_add', args=[self.task.pk, self.parameter.pk])

    def test_redirect_anonymous_on_score_creation(self):
        # WHEN anonymous user gets score creation page
        response = self.client.get(self.url)
        # THEN he is redirected to login page
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + self.url)

    @parameterized.expand([
        ('user', 403),
        ('org', 403),
        ('expertB', 200),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_score_creation_get(self, username, expected_response_code):
        self.client.login(username=username, password='password')

        # WHEN user gets score creation page
        response = self.client.get(self.url)

        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand([
        ('user',),
        ('org',),
    ])
    def test_forbid_unauthorized_score_creation(self, username):
        self.client.login(username=username, password='password')

        # WHEN unauthorized user forges and POSTs score creation form
        self.client.post(self.url, {
            'score-found': 0,
            'score-task': self.task.pk,
            'score-parameter': self.parameter.pk,
            'score-revision': Score.REVISION_DEFAULT
        })

        # THEN score does not get created
        self.assertEqual(0, Score.objects.count())


class ScoreViewsTestCase(TestCase):
    def setUp(self):
        # with csrf checking:
        self.client = Client(enforce_csrf_checks=True)

        # create expert B:
        self.expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        self.expertB.profile.is_expertB = True

        # create user:
        self.user = User.objects.create_user('user', 'user@svobodainfo.org', 'password')

        self.monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        self.organization = mommy.make(Organization, monitoring=self.monitoring)

        self.task = mommy.make(
            Task,
            organization=self.organization,
            user=self.expertB,
            status=Task.TASK_APPROVED,
        )
        self.parameter = mommy.make(
            Parameter,
            monitoring=self.monitoring,
        )
        self.score = mommy.make(
            Score,
            task=self.task,
            parameter=self.parameter,
        )

    def test_score(self):
        url = reverse('exmo2010:score_edit', args=[self.score.pk])

        # redirect for anonymous:
        resp = self.client.get(url, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertRedirects(resp, settings.LOGIN_URL + '?next=' + url)

        # expert B login:
        self.client.login(username=self.expertB.username, password=self.expertB.password)
        resp = self.client.get(url, follow=True)
        self.assertEqual(resp.status_code, 200)

        # send form:
        key_salt = "django.contrib.forms.CommentSecurityForm"
        timestamp = str(int(time.time()))
        object_pk = str(self.score.pk)
        content_type = str(self.score.__class__)

        value = "-".join((content_type, object_pk, timestamp))
        expected_hash = salted_hmac(key_salt, value).hexdigest()

        score = 1
        text = u'\u043e\u043e\u043e'

        form_data = {
            'found': score,
            'complete': score,
            'topical': score,
            'accessible': score,
            'hypertext': score,
            'document': score,
            'image': score,
            'foundComment': text,
            'completeComment': text,
            'topicalComment': text,
            'hypertextComment': text,
            'accessibleComment': text,
            'recomendation': text,
            'comment': text,
            'name': self.expertB.username,
            'email': self.expertB.email,
            'status': score,
            'timestamp': timestamp,
            'object_pk': object_pk,
            'content_type': content_type,
            'security_hash': expected_hash,
        }

        form = ScoreFormWithComment(self.score, data=form_data)
        self.assertEqual(form.is_valid(), True)


class AjaxGetRatingPlacesTestCase(TestCase):
    # Ajax request SHOULD return correct rating places for valid rating types

    def setUp(self):
        self.client = Client()
        # GIVEN interaction monitoring
        monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        # AND there are 2 approved tasks with organizations
        self.task1 = mommy.make(Task, organization__monitoring=monitoring, status=Task.TASK_APPROVED)
        self.task2 = mommy.make(Task, organization__monitoring=monitoring, status=Task.TASK_APPROVED)
        # AND 2 parameters (normative and recommendatory)
        kwargs = dict(complete=1, topical=1, accessible=1, hypertext=1, document=1, image=1)
        parameter1 = mommy.make(Parameter, monitoring=monitoring, weight=1, exclude=None, npa=True, **kwargs)
        parameter2 = mommy.make(Parameter, monitoring=monitoring, weight=2, exclude=None, **kwargs)
        # AND 2 scores for each task
        kwargs1 = dict(found=1, complete=2, topical=3, accessible=2, hypertext=1, document=1, image=1)
        kwargs2 = dict(found=1, complete=3, topical=1, accessible=1, hypertext=0, document=1, image=1)
        mommy.make(Score, task=self.task1, parameter=parameter1, **kwargs1)
        mommy.make(Score, task=self.task1, parameter=parameter2, **kwargs2)
        mommy.make(Score, task=self.task2, parameter=parameter1, **kwargs2)
        mommy.make(Score, task=self.task2, parameter=parameter2, **kwargs1)
        # AND expert A account
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND I am logged in as expert A
        self.client.login(username='expertA', password='password')

    def test_places_in_rating(self):
        # WHEN I get rating places with ajax
        url = reverse('exmo2010:ratingUpdate')
        response = self.client.get(url, {'task_id': self.task1.pk}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        # AND place by all parameters should be 2
        self.assertEqual(result['place_all'], 2)
        # AND place by normative parameters should be 1
        self.assertEqual(result['place_npa'], 1)
        # AND place by recommendatory parameters should be 2
        self.assertEqual(result['place_other'], 2)
