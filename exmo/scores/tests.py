# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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
from bs4 import BeautifulSoup
from contextlib import contextmanager

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from mock import Mock, patch
from model_mommy import mommy
from nose_parameterized import parameterized

from core.test_utils import OptimizedTestCase
from custom_comments.models import CommentExmo
from exmo2010.models import Monitoring, ObserversGroup, Organization, Parameter, Task, Score, UserProfile
from exmo2010.models.monitoring import INT, PUB, RATE
from scores.views import rating_update


class ScoreAddAccessTestCase(TestCase):
    # Only expertA and expertB assigned to task should be allowed to create score for it.

    def setUp(self):
        # GIVEN organization, parameter and task in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=RATE)
        param = mommy.make(Parameter, monitoring=org.monitoring)
        task = mommy.make(Task, organization=org)

        # AND user without any permissions
        User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND superuser
        User.objects.create_superuser('admin', 'admin@svobodainfo.org', 'password')
        # AND expert B, not assigned to the task
        other_expertB = User.objects.create_user('other_expertB', 'other_expertB@svobodainfo.org', 'password')
        other_expertB.profile.is_expertB = True
        # AND expert A
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.organization = [org]
        # AND observer user
        observer = User.objects.create_user('observer', 'observer@svobodainfo.org', 'password')
        # AND observers group for monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=org.monitoring)
        obs_group.organizations = [org]
        obs_group.users = [observer]

        self.url = reverse('exmo2010:score_add', args=[task.pk, param.pk])

    @parameterized.expand([
        (None, 302),
        ('user', 403),
        ('orguser', 403),
        ('observer', 403),
        ('other_expertB', 403),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_score_creation_get(self, username, expected_response_code):
        self.client.login(username=username, password='password')

        # WHEN user gets score creation page
        response = self.client.get(self.url)

        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand(zip(['user', 'orguser', 'observer', 'other_expertB']))
    def test_forbid_unauthorized_score_creation(self, username):
        self.client.login(username=username, password='password')

        # WHEN unauthorized user forges and POSTs score creation form
        response = self.client.post(self.url, {'found': 0})

        # THEN response status_code should be 403 (Forbidden)
        self.assertEqual(response.status_code, 403)

        # AND score does not get created
        self.assertEqual(0, Score.objects.count())

    def test_redirect_anonymous_post(self):
        # WHEN anonymous POSTs score creation form
        response = self.client.post(self.url, {'found': 0})
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to login page
        self.assertRedirects(response, '{}?next={}'.format(settings.LOGIN_URL, self.url))


class ScoreAddTestCase(TestCase):
    # ExpertA and expertB assigned to task should be able to create score for it.

    def setUp(self):
        # GIVEN expertA and expertB
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND organization and parameter in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=RATE)
        self.param = mommy.make(Parameter, monitoring=org.monitoring)
        # AND organization and parameter in MONITORING_INTERACTION monitoring
        org_interact = mommy.make(Organization, monitoring__status=INT)
        self.param_interact = mommy.make(Parameter, monitoring=org_interact.monitoring)
        # AND 2 tasks assigned to expertB
        self.task = mommy.make(Task, organization=org, user=expertB)
        self.task_interact = mommy.make(Task, organization=org_interact, user=expertB)

    @parameterized.expand([
        ('expertA',),
        ('expertB',),
    ])
    def test_create_score_rate(self, username):
        self.client.login(username=username, password='password')

        # WHEN user POSTs score creation form
        url = reverse('exmo2010:score_add', args=[self.task.pk, self.param.pk])
        response = self.client.post(url, {'found': 0, 'recommendations': '123'})

        # THEN response redirects to task scores list
        url = reverse('exmo2010:task_scores', args=[self.task.pk])
        self.assertRedirects(response, '%s#parameter_%s' % (url, self.param.code))

        # AND score get created
        self.assertEqual(1, Score.objects.count())

    @parameterized.expand([
        ('expertA',),
        ('expertB',),
    ])
    def test_create_score_interaction(self, username):
        self.client.login(username=username, password='password')

        # WHEN user POSTs score creation form
        url = reverse('exmo2010:score_add', args=[self.task_interact.pk, self.param_interact.pk])
        response = self.client.post(url, {'found': 0, 'recommendations': '123'})

        # THEN score get created
        self.assertEqual(1, Score.objects.count())

        # AND response redirects to score page
        score = Score.objects.get(task=self.task_interact.pk,
                                  parameter=self.param_interact.pk,
                                  revision=Score.REVISION_DEFAULT)
        self.assertRedirects(response, reverse('exmo2010:score', args=[score.pk]))


class ScoreEditInitialTestCase(TestCase):
    # TODO: Move this testcase to *general logic* tests directory.

    # ExpertA and expertB assigned to task should be able to edit score in RATE monitoring.

    # NOTE: See also ScoreEditInteractionTestCase for INTERACTION monitoring edit case.

    def setUp(self):
        # GIVEN expertA and expertB
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND organization and parameter in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=RATE)
        self.param = mommy.make(Parameter, monitoring=org.monitoring)
        # AND task assigned to expertB
        self.task = mommy.make(Task, organization=org, user=expertB)
        self.score = mommy.make(Score, task=self.task, parameter=self.param, found=1)

        self.url = reverse('exmo2010:score', args=[self.score.pk])

    @parameterized.expand([
        ('expertA',),
        ('expertB',),
    ])
    def test_edit_score(self, username):
        self.client.login(username=username, password='password')

        # WHEN user POSTs score edit form
        response = self.client.post(self.url, {'found': 0, 'recommendations': '123'})

        # THEN response redirects to task scores list
        url = reverse('exmo2010:task_scores', args=[self.task.pk])
        self.assertRedirects(response, '%s#parameter_%s' % (url, self.param.code))

        # AND score get updated in DB
        self.assertEqual(0, Score.objects.get(pk=self.score.pk).found)


class ScoreEditInteractionTestCase(TestCase):
    # TODO: Move this testcase to *general logic* tests directory.

    # ExpertA and expertB assigned to task should be able to edit score in INTERACTION monitoring.
    # Old score revision should be saved with new pk and 'last_modified' field in old score revision shouldn't change.
    # And comment should be added

    # NOTE: See also ScoreEditInitialTestCase for RATE monitoring edit case.

    def setUp(self):
        # GIVEN expertA and expertB
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND organization and parameter in MONITORING_INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=INT)
        self.param = mommy.make(Parameter, monitoring=org.monitoring)
        # AND task assigned to expertB
        self.task = mommy.make(Task, organization=org, user=expertB)
        self.score = mommy.make(Score, task=self.task, parameter=self.param, found=1)
        self.score_last_modified = self.score.last_modified

        self.url = reverse('exmo2010:score', args=[self.score.pk])

    @parameterized.expand([
        ('expertA',),
        ('expertB',),
    ])
    def test_edit_score(self, username):
        self.client.login(username=username, password='password')

        data = {'found': 0, 'score_%s-comment' % self.score.pk: '<p>lol</p>', 'recommendations': '123'}
        # WHEN user POSTs score edit form
        response = self.client.post(self.url, data)

        # THEN response redirects to score page
        self.assertRedirects(response, self.url)

        # AND old score revision get saved in DB
        old_revisions = Score.objects.filter(revision=Score.REVISION_INTERACT)
        self.assertEqual([(self.task.pk, self.param.pk, 1)],
                         list(old_revisions.values_list('task', 'parameter', 'found')))
        # AND 'last_modified' field in old score revision shouldn't change
        self.assertEqual(self.score_last_modified, old_revisions[0].last_modified)

        # AND score get updated in DB
        self.assertEqual(0, Score.objects.get(pk=self.score.pk).found)

        # AND comment get created
        self.assertEqual([u'<p>lol</p>'], list(CommentExmo.objects.values_list('comment', flat=True)))


class ScoreRecommendationsShouldChangeTestCase(TestCase):
    # TODO: Move this testcase to *validation* tests directory.

    # Recommendations SHOULD change when score is changed.
    # Exception cases, when recommendations MAY stay unchanged:
    #  * When score is reevaluated to maximum.
    #   - old scores in database, which have empty recommendations. (BUG 2069)
    #   - new criterion is added and score was maximum.
    #  * When monitoring phase is not INTERACTION or FINALIZING.
    #  * When monitoring has "no_interact" flag set to True.

    def setUp(self):
        # GIVEN i am logged in as expertA
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

        # AND organization  in MONITORING_INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=INT)
        # AND parameter with no optional criteria
        kwargs = dict(complete=0, topical=0, accessible=0, hypertext=0, document=0, image=0)
        self.param = mommy.make(Parameter, monitoring=org.monitoring, **kwargs)
        # AND maximum score with recommendations and found=1
        self.score = mommy.make(Score, task__organization=org, parameter=self.param, found=1, recommendations='123')

        self.url = reverse('exmo2010:score', args=[self.score.pk])

    def test_recommendations_should_change(self):
        """
        Recommendations SHOULD change when score is changed.
        """

        # WHEN i POST score edit form with the same recommendation and 'found' changed to 0
        response = self.client.post(self.url, {'found': 0, 'comment': 'lol', 'recommendations': '123'})

        # THEN score should stay unchanged in database
        self.assertEqual(list(Score.objects.values_list('pk', 'found')), [(self.score.pk, 1)])
        # AND response should contain recommendations error message
        self.assertContains(response, _('Recommendations should change when score is changed'), 1)

    def test_all_max(self):
        """
        Recommendations MAY stay unchanged when all score criteria changed to maximum.
        """

        # WHEN new 'accessible' criterion added to parameter
        Parameter.objects.filter(pk=self.param.pk).update(accessible=True)

        # AND i POST score edit form with the same recommendation and 'accessible' set to max (3)
        self.client.post(self.url, {'found': 1, 'accessible': 3, 'comment': 'lol', 'recommendations': '123'})

        # THEN score should get updated in database. Accessible should change from None to 3
        db_score = Score.objects.filter(pk=self.score.pk)
        self.assertEqual(list(db_score.values_list('found', 'accessible')), [(1, 3)])

    def test_monitoring_phase_initial_rate(self):
        """
        Recommendations MAY stay unchanged when monitoring phase is not INTERACTION or FINALIZING.
        """

        # WHEN monitoring phase is changed to INITIAL RATE
        Monitoring.objects.filter(pk=self.param.monitoring.pk).update(status=RATE)

        # AND i POST score edit form with the same recommendation and 'found' changed to 0
        self.client.post(self.url, {'found': 0, 'comment': 'lol', 'recommendations': '123'})

        # THEN score should get updated in database.
        db_score = Score.objects.filter(pk=self.score.pk)
        self.assertEqual(list(db_score.values('found')), [{'found': 0}])

    def test_monitoring_no_interact(self):
        """
        Recommendations MAY stay unchanged when monitoring "no_interact" flag set to True.
        """

        # WHEN monitoring "no_interact" flag set to True
        Monitoring.objects.filter(pk=self.param.monitoring.pk).update(no_interact=True)

        # AND i POST score edit form with the same recommendation and 'found' changed to 0
        self.client.post(self.url, {'found': 0, 'comment': 'lol', 'recommendations': '123'})

        # THEN score should get updated in database.
        db_score = Score.objects.filter(pk=self.score.pk)
        self.assertEqual(list(db_score.values('found')), [{'found': 0}])


class ScoreRecommendationsShouldExistTestCase(TestCase):
    # TODO: Move this testcase to *validation* tests directory.

    # Recommendations SHOULD exist when score is evaluated to non-maximum.
    # Exception cases, when recommendations MAY be omitted:
    #  * When monitoring has "no_interact" flag set to True.

    def setUp(self):
        # GIVEN i am logged in as expertA
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

        # AND organization  in MONITORING_INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=INT)
        # AND parameter with no optional criteria
        kwargs = dict(complete=0, topical=0, accessible=0, hypertext=0, document=0, image=0)
        self.param = mommy.make(Parameter, monitoring=org.monitoring, **kwargs)
        # AND maximum score with recommendations and found=1
        self.score = mommy.make(Score, task__organization=org, parameter=self.param, found=1, recommendations='123')

        self.url = reverse('exmo2010:score', args=[self.score.pk])

    def test_recommendations_should_exist(self):
        """
        Recommendations SHOULD exist when score is evaluated to non-maximum.
        """

        # WHEN i POST score edit form with empty recommendation and 'found' changed to 0 (non-max score)
        response = self.client.post(self.url, {'found': 0, 'comment': 'lol', 'recommendations': ''})

        # THEN score should stay unchanged in database
        self.assertEqual(list(Score.objects.values_list('pk', 'found', 'recommendations')), [(self.score.pk, 1, '123')])
        # AND response should contain recommendations error message
        self.assertContains(response, _('Score is not maximum, recommendations should exist'), 1)

    def test_all_max(self):
        """
        Recommendations MAY be omitted when all score criteria changed to maximum.
        """

        # WHEN new 'accessible' criterion added to parameter
        Parameter.objects.filter(pk=self.param.pk).update(accessible=True)

        # AND i POST score edit form with empty recommendation and 'accessible' set to max (3)
        self.client.post(self.url, {'found': 1, 'accessible': 3, 'comment': 'lol', 'recommendations': ''})

        # THEN score should get updated in database.
        # "Accessible" should change from None to 3, recommendations should become empty.
        db_score = Score.objects.filter(pk=self.score.pk)
        self.assertEqual(list(db_score.values_list('found', 'accessible', 'recommendations')), [(1, 3, '')])

    def test_monitoring_no_interact(self):
        """
        Recommendations MAY be omitted when monitoring "no_interact" flag set to True.
        """

        # WHEN monitoring "no_interact" flag set to True
        Monitoring.objects.filter(pk=self.param.monitoring.pk).update(no_interact=True)

        # AND i POST score edit form with empty recommendation and 'found' changed to 0 (non-max score)
        self.client.post(self.url, {'found': 0, 'comment': 'lol', 'recommendations': ''})

        # THEN score should get updated in database.
        # "Found" should change from 1 to 0, recommendations should become empty.
        db_score = Score.objects.filter(pk=self.score.pk)
        self.assertEqual(list(db_score.values_list('found', 'recommendations')), [(0, '')])


class AjaxGetRatingPlacesTestCase(TestCase):
    # Ajax request should return correct rating place

    def setUp(self):
        # GIVEN interaction monitoring
        monitoring = mommy.make(Monitoring, status=INT)
        # AND there are 2 approved tasks with organizations
        self.task1 = mommy.make(Task, organization__monitoring=monitoring, status=Task.TASK_APPROVED)
        self.task2 = mommy.make(Task, organization__monitoring=monitoring, status=Task.TASK_APPROVED)
        # AND 2 parameters (normative and recommendatory)
        kwargs = dict(complete=1, topical=1, accessible=1, hypertext=1, document=1, image=1)
        parameter1 = mommy.make(Parameter, monitoring=monitoring, weight=1, exclude=[], npa=True, **kwargs)
        parameter2 = mommy.make(Parameter, monitoring=monitoring, weight=2, exclude=[], **kwargs)
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
        url = reverse('exmo2010:rating_update')
        response = self.client.get(url, {'task_id': self.task1.pk}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        # AND place by all parameters should be 2
        self.assertEqual(result['rating_place'], 2)


class AjaxOpennessAccessTestCase(OptimizedTestCase):
    # Should allow to get rating place via ajax only if task is approved

    @classmethod
    def setUpClass(cls):
        super(AjaxOpennessAccessTestCase, cls).setUpClass()
        cls.users = {}
        # GIVEN interaction monitoring
        monitoring1 = mommy.make(Monitoring, status=INT)
        # AND published monitoring
        monitoring2 = mommy.make(Monitoring, status=PUB)
        # AND there are 3 organizations in interaction monitoring
        org1 = mommy.make(Organization, monitoring=monitoring1, name='org1')
        org2 = mommy.make(Organization, monitoring=monitoring1, name='org2')
        org3 = mommy.prepare(Organization, monitoring=monitoring1, name='org3')
        # AND there are 3 organizations in published monitoring
        org4 = mommy.prepare(Organization, monitoring=monitoring2, name='org4')
        org5 = mommy.prepare(Organization, monitoring=monitoring2, name='org5')
        org6 = mommy.prepare(Organization, monitoring=monitoring2, name='org6')
        # AND expert A
        cls.users['expertA'] = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        cls.users['expertA'].profile.is_expertA = True
        # AND expert B without tasks (expertB_free)
        cls.users['expertB_free'] = User.objects.create_user('expertB_free', 'usr@svobodainfo.org', 'password')
        cls.users['expertB_free'].profile.is_expertB = True
        # AND expert B with 3 tasks in each monitoring
        expertB_engaged = User.objects.create_user('expertB_engaged', 'usr@svobodainfo.org', 'password')
        expertB_engaged.profile.is_expertB = True
        cls.users['expertB_engaged'] = expertB_engaged
        cls.task_approved_interaction = mommy.prepare(
            Task, organization=org1, user=expertB_engaged, status=Task.TASK_APPROVED)
        cls.task_open_interaction = mommy.prepare(
            Task, organization=org2, user=expertB_engaged, status=Task.TASK_OPEN)
        cls.task_closed_interaction = mommy.prepare(
            Task, organization=org3, user=expertB_engaged, status=Task.TASK_CLOSED)
        cls.task_approved_published = mommy.prepare(
            Task, organization=org4, user=expertB_engaged, status=Task.TASK_APPROVED)
        cls.task_open_pub = mommy.prepare(
            Task, organization=org5, user=expertB_engaged, status=Task.TASK_OPEN)
        cls.task_closed_pub = mommy.prepare(
            Task, organization=org6, user=expertB_engaged, status=Task.TASK_CLOSED)
        # AND org representative
        cls.users['org_user'] = User.objects.create_user('org_user', 'usr@svobodainfo.org', 'password')
        cls.users['org_user'].profile.organization = [org1, org2]
        # AND just registered user
        cls.users['user'] = User.objects.create_user('user', 'usr@svobodainfo.org', 'password')

    @method_decorator(contextmanager)
    def mock_request(self, username, task):
        """
        Patch get_object_or_404 to return given task.
        Yield Mock request as context variable.
        """
        patch('scores.views.get_object_or_404', Mock(side_effect=lambda *a, **k: task)).start()
        yield Mock(user=self.users[username], method='GET', is_ajax=lambda: True, GET={'task_id': 1})
        patch.stopall()

    @parameterized.expand(zip(['expertA', 'org_user']))
    def test_interaction_approved_task_allow(self, username):
        with self.mock_request(username, self.task_approved_interaction) as request:
            self.assertEqual(rating_update(request).status_code, 200)

    @parameterized.expand(zip(['user']))
    def test_interaction_approved_task_forbid(self, username):
        with self.mock_request(username, self.task_approved_interaction) as request:
            self.assertRaises(PermissionDenied, rating_update, request)

    @parameterized.expand(zip('expertA org_user user expertB_free expertB_engaged'.split()))
    def test_published_approved_task_allow_all(self, username):
        with self.mock_request(username, self.task_approved_published) as request:
            self.assertEqual(rating_update(request).status_code, 200)

    @parameterized.expand(zip('expertA org_user user expertB_free expertB_engaged'.split()))
    def test_unapproved_task_forbid_all(self, username):
        for task in [
            self.task_open_pub, self.task_open_interaction, self.task_closed_interaction, self.task_closed_pub
        ]:
            with self.mock_request(username, task) as request:
                self.assertRaises(PermissionDenied, rating_update, request)


class AddExistingScoreRedirectTestCase(TestCase):
    # Score creation page should redirect to existing score page if score exists.

    def setUp(self):
        # GIVEN organization and parameter in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=RATE)
        param = mommy.make(Parameter, monitoring=org.monitoring)
        # AND expert B account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND open task assigned to expert B
        task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_OPEN)
        # AND score
        self.score = mommy.make(Score, task=task, parameter=param)
        # AND I am logged in as expert B
        self.client.login(username='expertB', password='password')
        self.score_add_url = reverse('exmo2010:score_add', args=(task.pk, param.pk))

    def test_get(self):
        # WHEN I get score creation page
        response = self.client.get(self.score_add_url)
        # THEN response should redirect to
        self.assertRedirects(response, reverse('exmo2010:score', args=(self.score.pk,)))

    def test_post(self):
        # WHEN I post to score creation page
        response = self.client.post(self.score_add_url)
        # THEN response should redirect to
        self.assertRedirects(response, reverse('exmo2010:score', args=(self.score.pk,)))


class AjaxPostScoreLinksTestCase(TestCase):
    # Posting score links should update score links field in database.
    # Response should contain properly cleaned and urlized new value

    def setUp(self):
        # GIVEN I am logged in as expert B
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        self.client.login(username='expertB', password='password')

        # AND organization and parameter in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=RATE)
        param = mommy.make(Parameter, monitoring=org.monitoring)

        # AND open task assigned to expert B
        task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_OPEN)
        # AND score
        self.score = mommy.make(Score, task=task, parameter=param, links='')

    def test_post(self):
        url = reverse('exmo2010:post_score_links', args=(self.score.pk,))
        link_string = '<p>123</p>\nhttp://123.ru\nhttp://456.ru'

        # WHEN I post score links with non-empty string
        response = self.client.post(url, {'links': link_string})

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND response should contain properly cleaned and urlized new value
        cleaned = BeautifulSoup('123<br/><a target="_blank" rel="nofollow" href="http://123.ru">http://123.ru</a>'
                                '<br/><a target="_blank" rel="nofollow" href="http://456.ru">http://456.ru</a>')
        self.assertEqual(BeautifulSoup(json.loads(response.content)['data']), cleaned)

        # AND score links should be updated in DB
        self.assertEqual(Score.objects.get(pk=self.score.pk).links, '<p>123</p>\nhttp://123.ru\nhttp://456.ru')

        # WHEN I post score links with empty string
        response = self.client.post(url, {'links': ''})

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND response should contain properly escaped and urlized new value
        self.assertEqual(json.loads(response.content)['data'], '')

        # AND score links should be updated in DB
        self.assertEqual(Score.objects.get(pk=self.score.pk).links, '')


class ForbidAjaxPostNonMaxScoreEmptyRecommandationsTestCase(TestCase):
    # Posting empty score recommendations for non-max score should be forbidden.

    def setUp(self):
        # GIVEN I am logged in as expert B
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        self.client.login(username='expertB', password='password')

        # AND organization and parameter in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=INT)
        param = mommy.make(Parameter, monitoring=org.monitoring)

        # AND open task assigned to expert B
        task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_OPEN)
        # AND score with found=0 and some recommendations
        self.score = mommy.make(Score, task=task, parameter=param, found=0, recommendations='123')
        self.score_add_url = reverse('exmo2010:score_add', args=(task.pk, param.pk))

    def test_post(self):
        url = reverse('exmo2010:post_recommendations', args=(self.score.pk,))

        # WHEN I post score recommendations with empty string
        response = self.client.post(url, {'recommendations': ''})
        # THEN response status_code should be 400 (Bad request)
        self.assertEqual(response.status_code, 400)
        # AND score recommendations should not be updated in DB
        self.assertEqual(Score.objects.get(pk=self.score.pk).recommendations, '123')


class AjaxSetPofileSettingTestCase(TestCase):
    # Posting ajax request SHOULD update fields in user profile.

    def setUp(self):
        # GIVEN organization in INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=INT)
        # AND organization representative with 'show_interim_score' setting turned on
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.show_interim_score = True
        orguser.profile.organization = [org]
        orguser.profile.save()
        # AND I am logged in as organization representative
        self.client.login(username='orguser', password='password')

    def test_post(self):
        url = reverse('exmo2010:ajax_set_profile_setting')
        # WHEN I post ajax-request with 'show_interim_score' set to False
        response = self.client.post(url, {'show_interim_score': 0}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND 'show_interim_score' should be updated to False
        self.assertEqual(User.objects.get(pk=1).profile.show_interim_score, False)


class RecommendationsTotalCostTestCase(TestCase):
    # TODO: Move this testcase to *general logic* tests directory.
    # exmo2010:recommendations

    # On Recommendations page total cost of recommendations should be displayed.

    def setUp(self):
        # GIVEN I am logged in as expertA
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

        # AND task in INTERACTION monitoring
        self.task = mommy.make(Task, organization__monitoring__status=INT)
        # AND 2 parameters of weight 1
        self.param1 = mommy.make(Parameter, monitoring=self.task.organization.monitoring, weight=1)
        self.param2 = mommy.make(Parameter, monitoring=self.task.organization.monitoring, weight=1)

        self.url = reverse('exmo2010:recommendations', args=(self.task.pk,))

    def test_all_finished_zero_total_cost(self):
        # WHEN two 100% scores added
        mommy.make(Score, task=self.task, parameter=self.param1, recommendations='a', found=1)
        mommy.make(Score, task=self.task, parameter=self.param2, recommendations='a', found=1)

        # AND i get recommendations page
        response = self.client.get(self.url)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND total_cost should be 0%
        self.assertEqual(response.context['total_cost'], 0.0)

    def test_100p_total_cost(self):
        # WHEN two 0% scores added
        mommy.make(Score, task=self.task, parameter=self.param1, recommendations='a', found=0)
        mommy.make(Score, task=self.task, parameter=self.param2, recommendations='a', found=0)

        # AND i get recommendations page
        response = self.client.get(self.url)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND total_cost should be 100%
        self.assertEqual(response.context['total_cost'], 100.0)

    def test_50p_total_cost(self):
        # WHEN 100% score is added
        mommy.make(Score, task=self.task, parameter=self.param1, recommendations='a', found=1)

        # AND 0% score is added
        mommy.make(Score, task=self.task, parameter=self.param2, recommendations='b', found=0)

        # AND i get recommendations page
        response = self.client.get(self.url)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND total_cost should be 50%
        self.assertEqual(response.context['total_cost'], 50.0)


class RecommendationsVisibilityNonrelevantTestCase(TestCase):
    # exmo2010:recommendations

    # TODO: Move this testcase to *general logic* tests directory.

    # On Recommendations page should be displayed scores with nonrelevant parameters, only if
    # that score has comments.
    # If there are no relevant scores, then current and initial cost of nonrelevant scores should be zero.

    def setUp(self):
        content_type = ContentType.objects.get_for_model(Score)

        # GIVEN I am logged in as expertA
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

        # AND organization in INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=INT)
        task = mommy.make(Task, organization=org)

        # AND score to nonrelevant parameter
        s_nonrelevant = mommy.make(Score, task=task, parameter__monitoring=org.monitoring)

        # AND score to nonrelevant parameter with recommendations
        s_nonrelevant_recomm = mommy.make(Score, task=task, parameter__monitoring=org.monitoring, recommendations='a')

        # AND score to nonrelevant parameter with comment
        s_nonrelevant_commented = mommy.make(Score, task=task, parameter__monitoring=org.monitoring)
        mommy.make(CommentExmo, object_pk=s_nonrelevant_commented.pk, content_type=content_type, user=expertA)

        # non-relevant parameters
        org.parameter_set = [
            s_nonrelevant_commented.parameter,
            s_nonrelevant.parameter,
            s_nonrelevant_recomm.parameter]

        self.url = reverse('exmo2010:recommendations', args=(task.pk,))

    def test_recommendations_list(self):
        # WHEN i get recommendations page
        response = self.client.get(self.url)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND exactly one nonrelevant score with cost of zero should be displayed.
        # (Nonrelevant score without comment should be hidden)
        self.assertEqual([s.cost for s in response.context['scores']], [0.0])


class RecommendationsVisibilityRelevantTestCase(TestCase):
    # exmo2010:recommendations

    # TODO: Move this testcase to *general logic* tests directory.

    # On Recommendations page relevant score should be displayed only if it has comments or recommendations.
    # Display order should be interim_cost.

    def setUp(self):
        content_type = ContentType.objects.get_for_model(Score)

        # GIVEN I am logged in as expertA
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

        # AND organization in INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=INT)
        self.task = mommy.make(Task, organization=org)

        # AND 0% score with recommendations
        # cost === 0.25 * (1 - 0) === 25%
        param = mommy.make(Parameter, monitoring=org.monitoring, weight=1)
        mommy.make(Score, task=self.task, parameter=param, recommendations='a', found=0)

        # AND 70%/85% interim/final scores with recommendations
        # interim cost === 0.25 * (1 - 0.7) === 0.075 (7.5%)
        # final cost === 0.25 * (1 - 0.85) === 0.0375 (3.75%)
        param = mommy.make(Parameter, monitoring=org.monitoring, weight=1, topical=True)
        mommy.make(
            Score,
            revision=Score.INTERIM,
            task=self.task,
            parameter=param,
            recommendations='a',
            found=1,
            topical=1)
        mommy.make(
            Score,
            revision=Score.FINAL,
            task=self.task,
            parameter=param,
            recommendations='a',
            found=1,
            topical=2)

        # AND 100% score with comment (0% cost)
        param = mommy.make(Parameter, monitoring=org.monitoring, weight=1)
        score_100_commented = mommy.make(Score, task=self.task, parameter=param, found=1)
        mommy.make(CommentExmo, object_pk=score_100_commented.pk, content_type=content_type, user=expertA)

        # AND 100% score
        param = mommy.make(Parameter, monitoring=org.monitoring, weight=1)
        mommy.make(Score, task=self.task, parameter=param, found=1)

    def test_recommendations_list(self):
        # WHEN i get recommendations page
        response = self.client.get(reverse('exmo2010:recommendations', args=(self.task.pk,)))

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND task openness should be 100 - 25 - 3.75 === 71.25%
        self.assertEqual(self.task.openness, 71.25)

        # AND scores with comments or recommendations should be displayed in order of interim_cost
        expected_cost_list = [
            25.0,  # 0% score,   25% interim_cost
            3.8,   # 85% score,  7.5% interim_cost
            0.0,   # 100% score, 0% interim_cost
            # 0.0  # 100% score without recommendations or comments, not displayed.
        ]
        self.assertEqual([s.cost for s in response.context['scores']], expected_cost_list)


class TaskScoresColumnsPickerTestCase(OptimizedTestCase):
    # exmo2010:task_scores

    # Should allow to configure and store submitted task-scores columns settings only if user is expert.
    # Non-experts should always see default columns.

    @classmethod
    def setUpClass(cls):
        super(TaskScoresColumnsPickerTestCase, cls).setUpClass()
        # GIVEN organization with task
        org = mommy.make(Organization, monitoring__status=INT)
        task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)
        # AND expert A
        cls.expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        cls.expertA.profile.is_expertA = True
        # AND org representative
        cls.org_user = User.objects.create_user('org_user', 'orguser@svobodainfo.org', 'password')
        cls.org_user.profile.organization = [org]
        # AND all users have all columns disabled in database.
        UserProfile.objects.update(**{
            'st_criteria': False,
            'st_score': False,
            'st_difference': False,
            'st_weight': False,
            'st_type': False
        })
        cls.url = reverse('exmo2010:task_scores', args=(task.pk,))

    def test__expert(self):
        # WHEN i login as expertA
        self.client.login(username='expertA', password='password')

        # AND i submit columns-picker form with only "st_criteria" enabled
        response = self.client.post(self.url, {'st_criteria': 'on', 'columns_picker_submit': True})

        # THEN i should be redirected to same page
        self.assertEqual(response.status_code, 302)

        # AND column settings should be stored in database
        expected_data = {
            'st_criteria': True,
            'st_score': False,
            'st_difference': False,
            'st_weight': False,
            'st_type': False,
        }
        profile = UserProfile.objects.filter(user=self.expertA)
        self.assertEqual(profile.values(*UserProfile.TASKSCORES_COLUMNS_FIELDS)[0], expected_data)

        # WHEN i get the task-scores page again
        response = self.client.get(self.url)

        # THEN response status_code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND only "st_criteria" column should be visible (as stored in database)
        visible = {col: response.context['columns_form'][col].value() for col in expected_data}
        self.assertEqual(visible, expected_data)

    def test__orguser(self):
        # WHEN i login as organization representative
        self.client.login(username='org_user', password='password')

        # AND i submit columns-picker form with only "st_criteria" enabled
        response = self.client.post(self.url, {'st_criteria': 'on', 'columns_picker_submit': True})

        # THEN i should be redirected to same page
        self.assertEqual(response.status_code, 302)

        # WHEN i get the task-scores page again
        response = self.client.get(self.url)

        # THEN response status_code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND default columns should be visible (ignoring database and submitted settings)
        expected_data = {
            'st_criteria': False,
            'st_score': True,
            'st_difference': True,
            'st_weight': False,
            'st_type': True,
        }
        visible = {col: response.context['columns_form'][col].value() for col in expected_data}
        self.assertEqual(visible, expected_data)
