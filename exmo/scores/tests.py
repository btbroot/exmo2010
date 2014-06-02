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
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _
from model_mommy import mommy
from nose_parameterized import parameterized

from custom_comments.models import CommentExmo
from exmo2010.models import *
from exmo2010.models.monitoring import Monitoring, RATE, MONITORING_INTERACTION


class ScoreAddAccessTestCase(TestCase):
    # Only expertA and expertB assigned to task should be allowed to create score for it.

    def setUp(self):
        # GIVEN organization, parameter and task in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_RATE)
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

        self.url = reverse('exmo2010:score_add', args=[task.pk, param.pk])

    @parameterized.expand([
        (None, 403),
        ('user', 403),
        ('orguser', 403),
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

    @parameterized.expand(zip([None, 'user', 'org', 'other_expertB']))
    def test_forbid_unauthorized_score_creation(self, username):
        self.client.login(username=username, password='password')

        # WHEN unauthorized user forges and POSTs score creation form
        response = self.client.post(self.url, {'found': 0})

        # THEN response status_code should be 403 (Forbidden)
        self.assertEqual(response.status_code, 403)

        # AND score does not get created
        self.assertEqual(0, Score.objects.count())


class ScoreAddTestCase(TestCase):
    # ExpertA and expertB assigned to task should be able to create score for it.

    def setUp(self):
        # GIVEN expertA and expertB
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND organization and parameter in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_RATE)
        self.param = mommy.make(Parameter, monitoring=org.monitoring)
        # AND organization and parameter in MONITORING_INTERACTION monitoring
        org_interact = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION)
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
        self.assertRedirects(response, reverse('exmo2010:score_view', args=[score.pk]))


class ScoreEditInitialTestCase(TestCase):
    # ExpertA and expertB assigned to task should be able to edit score in MONITORING_RATE monitoring.

    def setUp(self):
        # GIVEN expertA and expertB
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND organization and parameter in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_RATE)
        self.param = mommy.make(Parameter, monitoring=org.monitoring)
        # AND task assigned to expertB
        self.task = mommy.make(Task, organization=org, user=expertB)
        self.score = mommy.make(Score, task=self.task, parameter=self.param, found=1)

        self.url = reverse('exmo2010:score_view', args=[self.score.pk])

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

    # ExpertA and expertB assigned to task should be able to edit score in MONITORING_INTERACTION monitoring.
    # Old score revision should be saved with new pk and 'last_modified' field in old score revision shouldn't change.
    # And comment should be added

    def setUp(self):
        # GIVEN expertA and expertB
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND organization and parameter in MONITORING_INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION)
        self.param = mommy.make(Parameter, monitoring=org.monitoring)
        # AND task assigned to expertB
        self.task = mommy.make(Task, organization=org, user=expertB)
        self.score = mommy.make(Score, task=self.task, parameter=self.param, found=1)
        self.score_last_modified = self.score.last_modified

        self.url = reverse('exmo2010:score_view', args=[self.score.pk])

    @parameterized.expand([
        ('expertA',),
        ('expertB',),
    ])
    def test_edit_score(self, username):
        self.client.login(username=username, password='password')

        # WHEN user POSTs score edit form
        response = self.client.post(self.url, {'found': 0, 'comment': '<p>lol</p>', 'recommendations': '123'})

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

    def setUp(self):
        # GIVEN i am logged in as expertA
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

        # AND organization  in MONITORING_INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION)
        # AND parameter with no optional criteria
        kwargs = dict(complete=0, topical=0, accessible=0, hypertext=0, document=0, image=0)
        self.param = mommy.make(Parameter, monitoring=org.monitoring, **kwargs)
        # AND maximum score with recommendations and found=1
        self.score = mommy.make(Score, task__organization=org, parameter=self.param, found=1, recommendations='123')

        self.url = reverse('exmo2010:score_view', args=[self.score.pk])

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


class AjaxGetRatingPlacesTestCase(TestCase):
    # Ajax request should return correct rating places for valid rating types

    def setUp(self):
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
        url = reverse('exmo2010:rating_update')
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


class AjaxOpennessAccessTestCase(TestCase):
    # Should allow to get rating place via ajax only if task is approved
    # AND forbid access for expertB and regular user if monitoring is not published

    def setUp(self):
        # GIVEN interaction monitoring
        monitoring1 = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        # AND published monitoring
        monitoring2 = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        # AND there are 3 organizations in interaction monitoring
        org1 = mommy.make(Organization, monitoring=monitoring1, name='org1')
        org2 = mommy.make(Organization, monitoring=monitoring1, name='org2')
        org3 = mommy.make(Organization, monitoring=monitoring1, name='org3')
        # AND there are 3 organizations in published monitoring
        org4 = mommy.make(Organization, monitoring=monitoring2, name='org4')
        org5 = mommy.make(Organization, monitoring=monitoring2, name='org5')
        org6 = mommy.make(Organization, monitoring=monitoring2, name='org6')
        # AND expert A
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND expert B without tasks (expertB_free)
        expertB_free = User.objects.create_user('expertB_free', 'usr@svobodainfo.org', 'password')
        expertB_free.profile.is_expertB = True
        # AND expert B with 3 tasks in each monitoring
        expertB_engaged = User.objects.create_user('expertB_engaged', 'usr@svobodainfo.org', 'password')
        expertB_engaged.profile.is_expertB = True
        self.task_approved_interaction = mommy.make(
            Task, organization=org1, user=expertB_engaged, status=Task.TASK_APPROVED)
        self.task_open_interaction = mommy.make(
            Task, organization=org2, user=expertB_engaged, status=Task.TASK_OPEN)
        self.task_closed_interaction = mommy.make(
            Task, organization=org3, user=expertB_engaged, status=Task.TASK_CLOSED)
        self.task_approved_published = mommy.make(
            Task, organization=org4, user=expertB_engaged, status=Task.TASK_APPROVED)
        self.task_open_published = mommy.make(
            Task, organization=org5, user=expertB_engaged, status=Task.TASK_OPEN)
        self.task_closed_published = mommy.make(
            Task, organization=org6, user=expertB_engaged, status=Task.TASK_CLOSED)
        # AND org repersentative
        org_user = User.objects.create_user('org_user', 'usr@svobodainfo.org', 'password')
        org_user.profile.organization = [org1, org2]
        # AND just registered user
        User.objects.create_user('user', 'usr@svobodainfo.org', 'password')

        self.url = reverse('exmo2010:rating_update')

    @parameterized.expand([
        ('expertA', 200),
        ('org_user', 200),
        ('user', 403),
        ('expertB_free', 403),
        ('expertB_engaged', 403),
    ])
    def test_interaction_monitoring_and_approved_task_access(self, username, response_code):
        # WHEN I logged in
        self.client.login(username=username, password='password')
        # AND I sent ajax-request
        response = self.client.get(self.url, {'task_id': self.task_approved_interaction.pk}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # THEN response should have expected status_code
        self.assertEqual(response.status_code, response_code)

    @parameterized.expand([
        ('expertA',),
        ('org_user',),
        ('user',),
        ('expertB_free',),
        ('expertB_engaged',),
    ])
    def test_published_approved_task_allow_all(self, username):
        # WHEN I logged in
        self.client.login(username=username, password='password')
        # AND I sent ajax-request
        response = self.client.get(self.url, {'task_id': self.task_approved_published.pk}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # THEN response should have expected status_code
        self.assertEqual(response.status_code, 200)

    @parameterized.expand([
        ('expertA',),
        ('org_user',),
        ('user',),
        ('expertB_free',),
        ('expertB_engaged',),
    ])
    def test_unapproved_task_forbid_all(self, username):
        # WHEN I logged in
        self.client.login(username=username, password='password')
        # AND I sent ajax-request to not approved tasks
        for task_id in [
            self.task_open_published.pk,
            self.task_open_interaction.pk,
            self.task_closed_interaction.pk,
            self.task_closed_published.pk
        ]:
            response = self.client.get(self.url, {'task_id': task_id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            # THEN response should have expected status_code
            self.assertEqual(response.status_code, 403)


class AddExistingScoreRedirectTestCase(TestCase):
    # Score creation page should redirect to existing score page if score exists.

    def setUp(self):
        # GIVEN organization and parameter in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_RATE)
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
        self.assertRedirects(response, reverse('exmo2010:score_view', args=(self.score.pk,)))

    def test_post(self):
        # WHEN I post to score creation page
        response = self.client.post(self.score_add_url)
        # THEN response should redirect to
        self.assertRedirects(response, reverse('exmo2010:score_view', args=(self.score.pk,)))


class AjaxPostScoreLinksTestCase(TestCase):
    # Posting score links should update score links field in database.
    # Response should contain properly escaped and urlized new value

    def setUp(self):
        # GIVEN I am logged in as expert B
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        self.client.login(username='expertB', password='password')

        # AND organization and parameter in MONITORING_RATE monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_RATE)
        param = mommy.make(Parameter, monitoring=org.monitoring)

        # AND open task assigned to expert B
        task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_OPEN)
        # AND score
        self.score = mommy.make(Score, task=task, parameter=param, links='')

    def test_post(self):
        url = reverse('exmo2010:post_score_links', args=(self.score.pk,))

        # WHEN I post score links with non-empty string
        response = self.client.post(url, {'links': '<p>123</p>\nhttp://123.ru\nhttp://123.ru'})

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND response should contain properly escaped and urlized new value
        escaped = '&lt;p&gt;123&lt;/p&gt;<br /><a target="_blank" href="http://123.ru">http://123.ru</a><br /><a target="_blank" href="http://123.ru">http://123.ru</a>'
        self.assertEqual(json.loads(response.content)['data'], escaped)

        # AND score links should be updated in DB
        self.assertEqual(Score.objects.get(pk=self.score.pk).links, '<p>123</p>\nhttp://123.ru\nhttp://123.ru')

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
        org = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION)
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
        # GIVEN organization in MONITORING_INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION)
        # AND organization representative with 'show_score_rev1' equals True
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.show_score_rev1 = True
        orguser.profile.organization = [org]
        orguser.profile.save()
        # AND ajax url
        self.url = reverse('exmo2010:ajax_set_profile_setting')
        # AND I am logged in as organization representative
        self.client.login(username='orguser', password='password')

    def test_post(self):
        # WHEN I post ajax-request with 'show_score_rev1' equals False
        response = self.client.post(self.url, {'show_score_rev1': 0}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND 'show_score_rev1' should be updated in to False
        self.assertEqual(User.objects.get(pk=1).profile.show_score_rev1, False)
