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


class ScoreBreadcrumbsTestCase(TestCase):
    def setUp(self):
        # GIVEN breadcrumbs data
        self.crumbs = {
            'Monitoring': (_('Monitoring cycles'), reverse('exmo2010:monitoring_list')),
            'Ratings': (_('Ratings'), reverse('exmo2010:ratings')),
        }
        self.breadcrumb_html = '<span class="breadcrumb-arrow"></span><a href="%s">%s</a>'

        # AND expertB account
        self.expertB = User.objects.create_user('expertB', 'usr@svobodainfo.org', 'password')
        self.expertB.groups.add(Group.objects.get(name=self.expertB.profile.expertB_group))

        # AND published monitoring with score
        monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED, hidden=True)
        organization = mommy.make(Organization, monitoring=monitoring)
        task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)
        task_id = task.pk
        parameter = mommy.make(Parameter, monitoring=monitoring, weight=1)
        score = mommy.make(Score, task=task, parameter=parameter)
        score_id = score.pk
        self.client = Client()
        self.scores_list_url = reverse('exmo2010:score_list_by_task', args=[task_id])
        self.score_detail_url = reverse('exmo2010:score_view', args=[score_id])

    @parameterized.expand([
        ('Monitoring',),
        ('Ratings',),
    ])
    def test_rating_breadcrumbs(self, title):
        if title == 'Monitoring':
            self.client.login(username='expertB', password='password')
        ratings_html = self.breadcrumb_html % (self.crumbs[title][1], self.crumbs[title][0])

        # WHEN user requests scores list page
        response = self.client.get(self.scores_list_url)
        content = response.content.decode('utf-8')
        # THEN it contains expected breadcrumb title and URL
        self.assertTrue(ratings_html in content)

        # WHEN user requests score detail page
        response = self.client.get(self.score_detail_url)
        content = response.content.decode('utf-8')
        # THEN it contains expected breadcrumb title and URL
        self.assertTrue(ratings_html in content)