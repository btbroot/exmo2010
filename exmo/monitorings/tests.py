# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2016 IRSI LTD
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

from __future__ import unicode_literals

import datetime

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from django.utils.formats import get_format
from django.utils.translation import get_language
from model_mommy import mommy
from nose_parameterized import parameterized

from .forms import MonitoringCopyForm
from core.test_utils import OptimizedTestCase
from custom_comments.models import CommentExmo
from exmo2010.models import (Claim, Monitoring, ObserversGroup, OrgUser,
                             Organization, Parameter, Task, Score, UserProfile)
from exmo2010.models.monitoring import INT, PRE, PUB


class MonitoringDeleteTestCase(TestCase):
    # exmo2010:monitoring_delete

    # TODO: move this testcase to *general logic* tests directory

    # Should delete monitoring with all related objects from database.

    def setUp(self):
        # GIVEN monitoring, parameter, organization, task, score and claim
        self.monitoring = mommy.make(Monitoring, status=PRE)
        param = mommy.make(Parameter, monitoring=self.monitoring)
        org = mommy.make(Organization, monitoring=self.monitoring)
        task = mommy.make(Task, organization=org)
        score = mommy.make(Score, parameter=param, task=task)
        mommy.make(Claim, score=score)

        # AND i am logged in as expert A
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

    def test_monitoring_deletion(self):
        url = reverse('exmo2010:monitoring_delete', args=[self.monitoring.pk])

        # WHEN i post monitoring deletion request
        response = self.client.post(url, follow=True)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # THEN Claims, Scores, Tasks, Organizations, Parameters and Monitoring should get deleted
        self.assertEqual(Claim.objects.count(), 0)
        self.assertEqual(Score.objects.count(), 0)
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(Organization.objects.count(), 0)
        self.assertEqual(Parameter.objects.count(), 0)
        self.assertEqual(Monitoring.objects.count(), 0)


class RatingsAvgOpennessTestCase(TestCase):
    # exmo2010:ratings

    # TODO: move this testcase to *general logic* tests directory

    # Ratings page should correctly display average openness

    def setUp(self):
        attrs = {a: False for a in 'complete accessible topical hypertext document image npa'.split()}

        # GIVEN published monitoring with zero weight parameter (hence zero openness)
        self.monitoring_zero_weight = mommy.make(Monitoring, status=PUB)
        task = mommy.make(Task, organization__monitoring=self.monitoring_zero_weight, status=Task.TASK_APPROVED)
        parameter = mommy.make(Parameter, monitoring=self.monitoring_zero_weight, weight=0, **attrs)
        mommy.make(Score, task=task, parameter=parameter, found=1)

        # AND published monitoring with zero score (score found === 0)
        self.monitoring_zero_score = mommy.make(Monitoring, status=PUB)
        task = mommy.make(Task, organization__monitoring=self.monitoring_zero_score, status=Task.TASK_APPROVED)
        parameter = mommy.make(Parameter, monitoring=self.monitoring_zero_score, weight=1, **attrs)
        mommy.make(Score, task=task, parameter=parameter, found=0)

        # AND published monitoring with nonzero score (score found === 1)
        self.monitoring_nonzero_score = mommy.make(Monitoring, status=PUB)
        task = mommy.make(Task, organization__monitoring=self.monitoring_nonzero_score, status=Task.TASK_APPROVED)
        parameter = mommy.make(Parameter, monitoring=self.monitoring_nonzero_score, weight=1, **attrs)
        mommy.make(Score, task=task, parameter=parameter, found=1)

    def test_values(self):
        # WHEN user requests ratings page
        response = self.client.get(reverse('exmo2010:ratings'))

        # THEN server returns "OK" response
        self.assertEqual(response.status_code, 200)

        # AND output contains all three monitorings
        monitorings = {m.pk: m for m in response.context['monitoring_list']}
        self.assertEqual(len(monitorings), 3)

        # AND monitoring_zero_weight average openness should be None
        self.assertEqual(monitorings[self.monitoring_zero_weight.pk].avg_openness, None)
        # AND monitoring_zero_score average openness should be 0.0
        self.assertEqual(monitorings[self.monitoring_zero_score.pk].avg_openness, 0.0)
        # AND monitoring_nonzero_score average openness should be 100.0
        self.assertEqual(monitorings[self.monitoring_nonzero_score.pk].avg_openness, 100.0)


class RatingColumnsPickerTestCase(OptimizedTestCase):
    # exmo2010:monitoring_rating

    # TODO: move this testcase to *general logic* tests directory

    # Should allow registerd users to configure and store submitted rating columns settings.
    # Non-experts should never see 'rt_representatives' and 'rt_comment_quantity' columns.
    # Anonymous users should always see default columns.

    @classmethod
    def setUpClass(cls):
        super(RatingColumnsPickerTestCase, cls).setUpClass()

        # GIVEN organization and parameter in published monitoring.
        org = mommy.make(Organization, monitoring__status=PUB)
        param = mommy.make(Parameter, monitoring=org.monitoring)

        # AND a score in approved task.
        task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)
        mommy.make(Score, task=task, parameter=param)

        # AND expert A
        cls.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        cls.expertA.profile.is_expertA = True
        # AND org representative
        cls.org_user = User.objects.create_user('org_user', 'orguser@svobodainfo.org', 'password')
        mommy.make(OrgUser, organization=org, userprofile=cls.org_user.profile)

        # AND all users have all columns disabled in database.
        UserProfile.objects.update(**{
            'rt_initial_openness': False,
            'rt_final_openness': False,
            'rt_difference': False,
            'rt_representatives': False,
            'rt_comment_quantity': False,
            'rt_initial_recomm': False,
            'rt_done_recomm': False,
        })
        cls.url = reverse('exmo2010:monitoring_rating', args=(task.pk,))

    def test__expert(self):
        # WHEN i login as expertA
        self.client.login(username='expertA', password='password')

        # AND i submit columns-picker form with only "rt_representatives" enabled
        response = self.client.post(self.url, {'rt_representatives': 'on', 'columns_picker_submit': True})

        # THEN i should be redirected to same page
        self.assertEqual(response.status_code, 302)

        # AND column settings should be stored in database
        expected_data = {
            'rt_initial_openness': False,
            'rt_final_openness': False,
            'rt_difference': False,
            'rt_representatives': True,
            'rt_comment_quantity': False,
            'rt_initial_recomm': False,
            'rt_done_recomm': False,
        }
        profile = UserProfile.objects.filter(user=self.expertA)
        self.assertEqual(profile.values(*UserProfile.RATING_COLUMNS_FIELDS)[0], expected_data)

        # WHEN i get the rating page again
        response = self.client.get(self.url)

        # THEN response status_code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND only "rt_representatives" column should be visible (as stored in database)
        visible = {col: response.context['rating_columns_form'][col].value() for col in expected_data}
        self.assertEqual(visible, expected_data)

    def test__orguser(self):
        # WHEN i login as organization representative
        self.client.login(username='org_user', password='password')

        # AND i submit columns-picker form with only "rt_representatives" and "rt_initial_openness" enabled
        post_data = {
            'rt_representatives': 'on',   # forbidden column
            'rt_initial_openness': 'on',
            'columns_picker_submit': True
        }
        response = self.client.post(self.url, post_data)

        # THEN i should be redirected to same page
        self.assertEqual(response.status_code, 302)

        # AND only "rt_initial_openness" column should be visible (stored in database), but
        # forbidden column "rt_representatives" should not be visible.
        expected_data = {
            'rt_initial_openness': True,
            'rt_final_openness': False,
            'rt_difference': False,
            'rt_representatives': False,  # forbidden column
            'rt_comment_quantity': False,
            'rt_initial_recomm': False,
            'rt_done_recomm': False,
        }
        profile = UserProfile.objects.filter(user=self.org_user)
        self.assertEqual(profile.values(*UserProfile.RATING_COLUMNS_FIELDS)[0], expected_data)

        # WHEN i get the rating page again
        response = self.client.get(self.url)

        # THEN response status_code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND only "rt_initial_openness" column should be visible
        visible = {col: response.context['rating_columns_form'][col].value() for col in expected_data}
        self.assertEqual(visible, expected_data)

    def test__anonymous(self):
        # WHEN AnonymousUser submit columns-picker form with only "rt_representatives" enabled
        response = self.client.post(self.url, {'rt_representatives': 'on', 'columns_picker_submit': True})

        # THEN i should be redirected to same page
        self.assertEqual(response.status_code, 302)

        # WHEN i get the rating page again
        response = self.client.get(self.url)

        # THEN response status_code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND default columns should be visible (ignoring database and submitted settings)
        expected_data = {
            'rt_difference': True,
            'rt_final_openness': True,
            'rt_representatives': False,
            'rt_comment_quantity': False,
            'rt_initial_openness': False,
            'rt_initial_recomm': False,
            'rt_done_recomm': False,
        }
        visible = {col: response.context['rating_columns_form'][col].value() for col in expected_data}
        self.assertEqual(visible, expected_data)


class RatingTableValuesTestCase(TestCase):
    # exmo2010:monitoring_rating

    # Scenario: Output to Rating Table
    def setUp(self):
        # GIVEN published monitoring
        self.monitoring = mommy.make(Monitoring, status=PUB)
        self.monitoring_id = self.monitoring.pk
        self.url = reverse('exmo2010:monitoring_rating', args=[self.monitoring_id])
        organization = mommy.make(Organization, monitoring=self.monitoring)
        self.task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        mommy.make(Score, task=self.task, parameter=self.parameter, found=0)

    def test_rt_row_output(self):
        # WHEN user requests rating page
        response = self.client.get(self.url)
        o = response.context['rating_list'][0]
        # THEN output data equals default values for organization
        self.assertEqual(o, self.task)
        self.assertEqual(o.place, 1)
        self.assertEqual(o.repr_len, 0)
        self.assertEqual(o.active_repr_len, 0)
        self.assertEqual(o.num_comments, 0)
        self.assertEqual(o.openness, 0)
        self.assertEqual(o.openness_initial, 0)
        self.assertEqual(o.openness_delta, 0.0)

    def test_rt_stats_output(self):
        # WHEN user requests rating page
        response = self.client.get(self.url)
        a = response.context['rating_stats']
        # THEN output average data equals expected values
        self.assertEqual(a['num_approved_tasks'], 1)
        self.assertEqual(a['num_rated_tasks'], 1)

        self.assertEqual(a['avg_repr_len'], 0)
        self.assertEqual(a['avg_active_repr_len'], 0)
        self.assertEqual(a['avg_num_comments'], 0)
        self.assertEqual(a['avg_interim_recommends_len'], 0)
        self.assertEqual(a['avg_done_recommends_len'], 0)

        self.assertEqual(a['sum_repr_len'], 0)
        self.assertEqual(a['sum_active_repr_len'], 0)
        self.assertEqual(a['sum_num_comments'], 0)
        self.assertEqual(a['sum_interim_recommends_len'], 0)
        self.assertEqual(a['sum_done_recommends_len'], 0)

        self.assertEqual(a['openness'], 0)
        self.assertEqual(a['openness_initial'], 0)
        self.assertEqual(a['openness_delta'], 0.0)


class NameFilterRatingTestCase(TestCase):
    # exmo2010:monitoring_rating

    # If name filter given on rating page, should show only filtered orgs

    def setUp(self):
        # GIVEN monitoring with 2 organizations
        monitoring = mommy.make(Monitoring, status=PUB)
        monitoring_id = monitoring.pk
        organization1 = mommy.make(Organization, name='org1', monitoring=monitoring)
        organization2 = mommy.make(Organization, name='org2', monitoring=monitoring)

        # AND two corresponding tasks, parameters, and scores for organizations
        task1 = mommy.make(Task, organization=organization1, status=Task.TASK_APPROVED)
        task2 = mommy.make(Task, organization=organization2, status=Task.TASK_APPROVED)
        parameter1 = mommy.make(Parameter, monitoring=monitoring, weight=1)
        parameter2 = mommy.make(Parameter, monitoring=monitoring, weight=1)
        mommy.make(Score, task=task1, parameter=parameter1)
        mommy.make(Score, task=task2, parameter=parameter2)

        self.url = reverse('exmo2010:monitoring_rating', args=[monitoring_id])

    @parameterized.expand([
        ('org1', ['org1']),
        ('org', ['org1', 'org2']),
        ('qwe', []),
    ])
    def test_org_filter(self, filter_str, expected_org_names):
        # WHEN user requests rating page with name_filter
        response = self.client.get(self.url, {'name': filter_str})

        # THEN only expected orgs should be shown
        org_names = set(t.organization.name for t in response.context['rating_list'])
        self.assertEqual(set(expected_org_names), org_names)


class RatingActiveRepresentativesTestCase(TestCase):
    # exmo2010:monitoring_rating

    # Should count active and total organizations representatives on rating page

    def setUp(self):
        # GIVEN User instance and two connected organizations to it
        monitoring = mommy.make(Monitoring, status=PUB)
        organization1 = mommy.make(Organization, name='org1', monitoring=monitoring)
        organization2 = mommy.make(Organization, name='org2', monitoring=monitoring)

        self.orguser = User.objects.create_user('usr', 'usr@svobodainfo.org', 'password')
        mommy.make(OrgUser, organization=organization1, userprofile=self.orguser.profile)
        mommy.make(OrgUser, organization=organization2, userprofile=self.orguser.profile)

        # AND two corresponding tasks, parameters, and scores for organizations
        task1 = mommy.make(Task, organization=organization1, status=Task.TASK_APPROVED)
        task2 = mommy.make(Task, organization=organization2, status=Task.TASK_APPROVED)
        parameter1 = mommy.make(Parameter, monitoring=monitoring, weight=1)
        parameter2 = mommy.make(Parameter, monitoring=monitoring, weight=1)
        self.score1 = mommy.make(Score, pk=1, task=task1, parameter=parameter1)
        self.score2 = mommy.make(Score, pk=2, task=task2, parameter=parameter2)
        self.content_type = ContentType.objects.get_for_model(Score)
        self.site = Site.objects.get_current()
        # AND superuser
        self.admin = User.objects.create_superuser('admin', 'admin@svobodainfo.org', 'password')

        self.url = reverse('exmo2010:monitoring_rating', args=[monitoring.pk])

    def test_first_org_active_users(self):
        # WHEN representative adds a comment to first task's score
        comment = CommentExmo(content_type=self.content_type, object_pk=self.score1.pk, user=self.orguser, site=self.site)
        comment.save()

        # AND requests rating page for monitoring
        response = self.client.get(self.url)
        tasks = dict((t.organization.name, t) for t in response.context['rating_list'])
        t1 = tasks['org1']
        t2 = tasks['org2']

        # THEN representatives quantity for every organization equals 1
        self.assertEqual(t1.repr_len, 1)
        self.assertEqual(t2.repr_len, 1)

        # AND active representatives quantity for first organization equals 1 (because of comment)
        self.assertEqual(t1.active_repr_len, 1)

        # AND active representatives quantity for second organization equals 0 (because of absence of comment)
        self.assertEqual(t2.active_repr_len, 0)

    def test_second_org_active_users(self):
        # WHEN representative adds two comments to second task's score
        comment = CommentExmo(content_type=self.content_type, object_pk=self.score2.pk, user=self.orguser, site=self.site)
        comment.save()
        comment = CommentExmo(content_type=self.content_type, object_pk=self.score2.pk, user=self.orguser, site=self.site)
        comment.save()

        # AND requests rating page for monitoring
        response = self.client.get(self.url)
        tasks = dict((t.organization.name, t) for t in response.context['rating_list'])
        t2 = tasks['org2']

        # THEN active representatives quantity for second organization equals 1
        self.assertEqual(t2.active_repr_len, 1)

    def test_non_existing_score_comments(self):
        # GIVEN comment to non-existing score
        comment = CommentExmo(content_type=self.content_type, object_pk=3, user=self.orguser, site=self.site)
        comment.save()

        # WHEN user requests rating page for monitoring
        response = self.client.get(self.url)
        tasks = dict((t.organization.name, t) for t in response.context['rating_list'])
        t1 = tasks['org1']
        t2 = tasks['org2']

        # THEN representatives quantity for every organization equals 1
        self.assertEqual(t1.repr_len, 1)
        self.assertEqual(t2.repr_len, 1)

        # AND active representatives quantity for all organizations equals 0
        self.assertEqual(t1.active_repr_len, 0)
        self.assertEqual(t2.active_repr_len, 0)

    def test_representatives_quantities_rendered(self):
        # WHEN superuser logs in (to see full table)
        self.client.login(username="admin", password="password")
        # AND requests rating page for monitoring
        response = self.client.get(self.url)

        soup = BeautifulSoup(response.content)
        td = soup.find('td', {'class': 'representatives'})
        representatives = td.strong.string

        # THEN table cell contents string with correct order of users quantity
        self.assertEqual(representatives, "1.0 / 0.0")


class HiddenMonitoringVisibilityTestCase(TestCase):
    # exmo2010:ratings

    # TODO: move this testcase to *permissions* tests directory
    # TODO: split in few separate testcases for each view.

    def setUp(self):
        # GIVEN hidden published monitoring
        self.monitoring = mommy.make(Monitoring, status=PUB, hidden=True)
        self.monitoring_id = self.monitoring.pk

        # AND organization connected to monitoring
        organization = mommy.make(Organization, monitoring=self.monitoring)

        # AND expertB connected to organization
        self.expertB = User.objects.create_user('expertB', 'expertb@svobodainfo.org', 'password')
        self.expertB.groups.add(Group.objects.get(name=self.expertB.profile.expertB_group))

        # AND representative connected to organization
        self.orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        self.orguser.groups.add(Group.objects.get(name=self.orguser.profile.organization_group))
        profile = self.orguser.get_profile()
        mommy.make(OrgUser, organization=organization, userprofile=profile)

        # AND expertA
        self.expertA = User.objects.create_user('expertA', 'experta@svobodainfo.org', 'password')
        self.expertA.groups.add(Group.objects.get(name=self.expertA.profile.expertA_group))

        # AND superuser
        self.su = User.objects.create_superuser('su', 'su@svobodainfo.org', 'password')

        # AND task, parameter and score
        self.task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED, user=self.expertB)
        parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        self.score = mommy.make(Score, task=self.task, parameter=parameter)

        # AND regular user
        self.usr = User.objects.create_user('usr', 'usr@svobodainfo.org', 'password')

        # AND observer user
        observer = User.objects.create_user('observer', 'observer@svobodainfo.org', 'password')
        # AND observers group for published hidden monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=self.monitoring)
        obs_group.organizations = [organization]
        obs_group.users = [observer]

        # AND expertB not connected to task
        self.expertB_out = User.objects.create_user('expertB_out', 'expertb.out@svobodainfo.org', 'password')
        self.expertB_out.groups.add(Group.objects.get(name=self.expertB_out.profile.expertB_group))

        # AND organization representative not connected to task
        self.orguser_out = User.objects.create_user('orguser_out', 'orguser.out@svobodainfo.org', 'password')
        self.orguser_out.groups.add(Group.objects.get(name=self.orguser_out.profile.organization_group))

    @parameterized.expand([
        ('expertB',),
        ('orguser',),
        ('expertA',),
        ('su',),
        ('observer',),
    ])
    def test_allowed_users_see_monitoring(self, username):
        # WHEN user logging in
        self.client.login(username=username, password='password')
        # AND requests ratings page
        response = self.client.get(reverse('exmo2010:ratings'))
        response_monitoring = response.context['monitoring_list'][0]
        # THEN response's context contains hidden monitoring in monitoring list
        # for connected organization representative, connected observer, connected expertB, expertA and superuser
        self.assertEqual(response_monitoring, self.monitoring)

    @parameterized.expand(zip([None, 'usr', 'expertB_out', 'orguser_out']))
    def test_forbidden_users_do_not_see_monitoring(self, username):
        # WHEN user logging in
        self.client.login(username=username, password='password')
        # AND requests ratings page
        response = self.client.get(reverse('exmo2010:ratings'))
        response_monitoring_list = response.context['monitoring_list']
        # THEN response's context contains no monitoring in monitoring list
        # for disconnected organization representative, disconnected expertB, anonymous and regular user
        self.assertEqual(len(response_monitoring_list), 0)

    # TODO: move out into new testcase
    @parameterized.expand(zip(['usr', 'expertB_out', 'orguser_out']))
    def test_forbid_hidden_score_page(self, username):
        # WHEN i log in
        self.client.login(username=username, password='password')

        # AND i request score page
        response = self.client.get(reverse('exmo2010:score', args=[self.score.pk]))

        # THEN response status_code is 403 (forbidden)
        self.assertEqual(response.status_code, 403)

    # TODO: move out into new testcase
    def test_redirect_anonymous_task_page(self):
        url = reverse('exmo2010:task_scores', args=[self.task.pk])
        # WHEN anonymous get task page
        response = self.client.get(url)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to login page
        self.assertRedirects(response, '{}?next={}'.format(settings.LOGIN_URL, url))

    # TODO: move out into new testcase
    @parameterized.expand(zip(['usr', 'expertB_out', 'orguser_out']))
    def test_forbid_hidden_task_page(self, username):
        # WHEN i log in
        self.client.login(username=username, password='password')

        # AND i request task page
        response = self.client.get(reverse('exmo2010:task_scores', args=[self.task.pk]))

        # THEN response status_code is 403 (forbidden)
        self.assertEqual(response.status_code, 403)

    # TODO: move out into new testcase
    def test_redirect_anonymous_score_page(self):
        url = reverse('exmo2010:score', args=[self.score.pk])
        # WHEN anonymous get score page
        response = self.client.get(url)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to login page
        self.assertRedirects(response, '{}?next={}'.format(settings.LOGIN_URL, url))


class RatingStatsTestCase(TestCase):
    # exmo2010:monitoring_rating

    # TODO: move this testcase into *general logic* tests directory

    # Should properly calculate rating statistics

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring, openness_expression__code=8, status=PUB)
        # AND 1 organization in this monitoring
        self.organization = mommy.make(Organization, monitoring=self.monitoring)
        # AND 2 approved tasks
        self.tasks = mommy.make(Task, organization=self.organization, status=Task.TASK_APPROVED, _quantity=2)
        # AND 2 parameters with positive weight
        self.parameters = mommy.make(Parameter, monitoring=self.monitoring, weight=1, exclude=[], _quantity=2,
                                     complete=1, topical=1, accessible=1, hypertext=1, document=1, image=1)
        # AND 2 scores for each parameter
        mommy.make(Score, task=self.tasks[0], parameter=self.parameters[0],
                   found=1, complete=3, topical=3, accessible=3, hypertext=1, document=1, image=1)
        mommy.make(Score, task=self.tasks[0], parameter=self.parameters[1],
                   found=1, complete=3, topical=3, accessible=2, hypertext=1, document=1, image=1)
        mommy.make(Score, task=self.tasks[1], parameter=self.parameters[0],
                   found=1, complete=2, topical=3, accessible=3, hypertext=1, document=1, image=1)
        mommy.make(Score, task=self.tasks[1], parameter=self.parameters[1],
                   found=1, complete=3, topical=3, accessible=1, hypertext=1, document=1, image=1)

        self.url = reverse('exmo2010:monitoring_rating', args=[self.monitoring.pk])

    def test_rating_without_params(self):
        # WHEN rating is requested without parameters
        response = self.client.get(self.url)
        stats = response.context['rating_stats']

        # THEN stats have expected results
        self.assertEqual(stats['openness'], 83.75)
        self.assertEqual(stats['openness_initial'], 83.75)
        self.assertEqual(stats['openness_delta'], 0.0)
        self.assertEqual(stats['num_rated_tasks'], len(self.tasks))

    @parameterized.expand([
        (0, 75.0),
        (1, 92.5),
    ])
    def test_rating_with_parameters(self, param_index, expected_openness):
        # WHEN rating is requested for one parameter
        response = self.client.get(self.url, {'type': 'user', 'params': [self.parameters[param_index].pk]})
        stats = response.context['rating_stats']

        # THEN stats have expected results
        self.assertEqual(stats['openness'], expected_openness)
        self.assertEqual(stats['openness_initial'], expected_openness)
        self.assertEqual(stats['openness_delta'], 0.0)
        self.assertEqual(stats['num_rated_tasks'], len(self.tasks))


class RatingStatsOrgCountTestCase(TestCase):
    # exmo2010:monitoring_rating

    # Rating stats with 'user' rating_type should
    # proprely count rated and total organizations

    def setUp(self):
        # GIVEN interaction monitoring
        self.monitoring = mommy.make(Monitoring, status=INT)
        # AND 2 organizations
        organization1 = mommy.make(Organization, name='org1', monitoring=self.monitoring)
        organization2 = mommy.make(Organization, name='org2', monitoring=self.monitoring)
        # AND 2 tasks
        self.task1 = mommy.make(Task, organization=organization1, status=Task.TASK_APPROVED)
        self.task2 = mommy.make(Task, organization=organization2, status=Task.TASK_APPROVED)
        # AND parameter with excluded organization2
        self.parameter1 = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        self.parameter1.exclude.add(organization2)
        # AND parameter without excluded organizations
        self.parameter2 = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        # AND 2 scores for each task
        mommy.make(Score, task=self.task1, parameter=self.parameter1)
        mommy.make(Score, task=self.task1, parameter=self.parameter2)
        mommy.make(Score, task=self.task2, parameter=self.parameter1)
        mommy.make(Score, task=self.task2, parameter=self.parameter2)
        # AND expert A account
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True
        # AND monitoring rating page url
        self.url = reverse('exmo2010:monitoring_rating', args=[self.monitoring.pk])
        # AND I am logged in as expert A
        self.client.login(username='expertA', password='password')

    def test_count_tasks(self):
        # WHEN I get monitoring rating page with users parameters
        response = self.client.get(self.url, {'type': 'user', 'params': self.parameter1.pk})
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND count of approved tasks should be 2
        self.assertEqual(response.context['rating_stats']['num_approved_tasks'], 2)
        # AND count of rated tasks should be 1
        self.assertEqual(response.context['rating_stats']['num_rated_tasks'], 1)


class StatisticsActiveOrganizationRepresentsTestCase(TestCase):
    # Monitorings statistics should contain correct count of active users

    def setUp(self):
        # GIVEN interaction monitoring
        self.monitoring = mommy.make(Monitoring, status=INT)
        # AND 2 organizations connected to monitoring
        organization1 = mommy.make(Organization, name='org1', monitoring=self.monitoring)
        organization2 = mommy.make(Organization, name='org2', monitoring=self.monitoring)
        # AND 2 approved tasks connected to organizations
        task1 = mommy.make(Task, organization=organization1, status=Task.TASK_APPROVED)
        task2 = mommy.make(Task, organization=organization2, status=Task.TASK_APPROVED)
        # AND parameter connected to monitoring
        parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        # AND 1 score for each task
        self.score1 = mommy.make(Score, task=task1, parameter=parameter)
        self.score2 = mommy.make(Score, task=task2, parameter=parameter)
        # AND organization representative connected to the first organization
        self.orguser1 = User.objects.create_user('org1', 'org@svobodainfo.org', 'password')
        self.orguser1.groups.add(Group.objects.get(name=self.orguser1.profile.organization_group))
        mommy.make(OrgUser, organization=organization1, userprofile=self.orguser1.profile)
        # AND one more organization representative connected to both organizations
        self.orguser2 = User.objects.create_user('org2', 'org@svobodainfo.org', 'password')
        self.orguser2.groups.add(Group.objects.get(name=self.orguser2.profile.organization_group))
        mommy.make(OrgUser, organization=organization1, userprofile=self.orguser2.profile)
        mommy.make(OrgUser, organization=organization2, userprofile=self.orguser2.profile)
        # AND content_type
        self.content_type = ContentType.objects.get_for_model(Score)
        # AND domain
        self.site = Site.objects.get_current()

    def test_two_orgs_posted_comments_in_one_organization(self):
        # WHEN 2 representatives post comments to the same organization
        comm1 = CommentExmo(content_type=self.content_type, object_pk=self.score1.pk, user=self.orguser1, site=self.site)
        comm1.save()
        comm2 = CommentExmo(content_type=self.content_type, object_pk=self.score1.pk, user=self.orguser2, site=self.site)
        comm2.save()
        statistics = self.monitoring.statistics()
        # THEN active orgusers count in monitoring statistics should equal 2
        self.assertEqual(statistics['organization_users_active'], 2)

    def test_one_org_posted_comments_in_two_organization(self):
        # WHEN 1 representative posts comments to 2 different organizations
        comm1 = CommentExmo(content_type=self.content_type, object_pk=self.score1.pk, user=self.orguser2, site=self.site)
        comm1.save()
        comm2 = CommentExmo(content_type=self.content_type, object_pk=self.score2.pk, user=self.orguser2, site=self.site)
        comm2.save()
        statistics = self.monitoring.statistics()
        # THEN active orgusers count in monitoring statistics should equal 1
        self.assertEqual(statistics['organization_users_active'], 1)


class MonitoringCopyFormTestCase(TestCase):
    # MonitoringCopyForm should validate user form and return corrected values

    @parameterized.expand([
        (['all'], {'all'}),
        (['parameters'], {'parameters'}),
        (['tasks'], {'tasks'}),
        (['all_scores'], set([])),
        (['current_scores'], set([])),
        (['representatives'], {'representatives'}),
        (['parameters', 'all_scores', 'representatives'], {'parameters', 'representatives'}),
        (['organizations', 'tasks', 'all_scores', 'current_scores'], {'organizations', 'tasks'}),
        (['parameters', 'tasks', 'current_scores'], {'parameters', 'tasks', 'current_scores'}),
        (['parameters', 'tasks', 'all_scores'], {'parameters', 'tasks', 'all_scores'}),
        (['all', 'current_scores'], {'all'}),
    ])
    def test_donors_field_validate(self, donors_list, expected_list):
        # WHEN I fill data monitoring copy form
        now = datetime.datetime.now().strftime(get_format('DATE_INPUT_FORMATS')[0])
        form_data = {
            'name_%s' % get_language(): 'monitoring name',
            'status': PRE,
            'openness_expression': 8,
            'donors': donors_list,
            'rate_date': now,
            'interact_date': now,
            'finishing_date': now,
            'publish_date': now,
        }
        form = MonitoringCopyForm(data=form_data)
        # THEN form should be valid
        self.assertEqual(form.is_valid(), True)
        # AND 'donors' field should contain expected list of values
        self.assertEqual(form.cleaned_data['donors'], expected_list)


class RatingRecommendationsStatsTestCase(TestCase):
    # exmo2010:monitoring_rating

    # TODO: move this testcase into *general logic* tests directory

    # Interim recommendations count and done recommendations count should be properly calculated

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)

        # AND parameter of nonzero weight
        self.param1 = mommy.make(Parameter, monitoring=self.monitoring, weight=1)

        # AND approved task
        self.task = mommy.make(Task, status=Task.TASK_APPROVED, organization__monitoring=self.monitoring)

        # AND I am logged in as expert A
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

        self.url = reverse('exmo2010:monitoring_rating', args=[self.monitoring.pk])

    def test1(self):
        # GIVEN interim score with recommendations
        mommy.make(Score, revision=Score.INTERIM, task=self.task, parameter=self.param1, recommendations='lol')
        # AND final score without recommendations
        mommy.make(Score, revision=Score.FINAL, task=self.task, parameter=self.param1, recommendations='')

        # WHEN I get rating page
        response = self.client.get(self.url)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND count of interim recommendations should be 1
        self.assertEqual(response.context['rating_list'][0].interim_recommends_len, 1)
        # AND count of done recommendations should be 1
        self.assertEqual(response.context['rating_list'][0].done_recommends_len, 1)

    def test2(self):
        # GIVEN final score without recommendations
        mommy.make(Score, revision=Score.FINAL, task=self.task, parameter=self.param1, recommendations='')

        # WHEN I get rating page
        response = self.client.get(self.url)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND count of interim recommendations should be 0
        self.assertEqual(response.context['rating_list'][0].interim_recommends_len, 0)
        # AND count of done recommendations should be 0
        self.assertEqual(response.context['rating_list'][0].done_recommends_len, 0)

    def test3(self):
        # GIVEN final score with recommendations
        mommy.make(Score, revision=Score.FINAL, task=self.task, parameter=self.param1, recommendations='lol')

        # WHEN I get rating page
        response = self.client.get(self.url)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND count of interim recommendations should be 1
        self.assertEqual(response.context['rating_list'][0].interim_recommends_len, 1)
        # AND count of done recommendations should be 0
        self.assertEqual(response.context['rating_list'][0].done_recommends_len, 0)


class CopyMonitoringViewTestCase(TestCase):
    # exmo2010:monitoring_copy

    # TODO: move this testcase into *general logic* tests directory

    # monitoring copy should be created

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND 3 organizations connected to monitoring
        self.orgs = mommy.make(Organization, monitoring=self.monitoring, _quantity=3)
        # AND parameter connected to monitoring
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring)
        # AND expert A account
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True
        # AND expert B account
        self.expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        self.expertB.profile.is_expertB = True
        # AND orguser
        self.orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        mommy.make(OrgUser, organization=self.orgs[0], userprofile=self.orguser.profile)
        # AND 3 approved tasks connected to organizations
        task1 = mommy.make(Task, organization=self.orgs[0], user=self.expertB, status=Task.TASK_APPROVED)
        task2 = mommy.make(Task, organization=self.orgs[1], user=self.expertB, status=Task.TASK_APPROVED)
        task3 = mommy.make(Task, organization=self.orgs[2], user=self.expertB, status=Task.TASK_APPROVED)
        # AND 1 score for each task
        mommy.make(Score, task=task1, parameter=self.parameter)
        mommy.make(Score, task=task2, parameter=self.parameter)
        mommy.make(Score, task=task3, parameter=self.parameter)
        # AND monitoring copy page url
        self.url = reverse('exmo2010:monitoring_copy', args=[self.monitoring.pk])
        # AND I am logged in as expert A
        self.client.login(username='expertA', password='password')

    def test_copy_monitoring(self):
        # WHEN I post monitoring copy form
        now = datetime.datetime.now().strftime(get_format('DATE_INPUT_FORMATS')[0])
        self.client.post(self.url, {
            'name_%s' % get_language(): 'monitoring name',
            'status': PRE,
            'openness_expression': 8,
            'donors': ['parameters', 'tasks', 'all_scores', 'representatives'],
            'rate_date': now,
            'interact_date': now,
            'finishing_date': now,
            'publish_date': now,
        })
        # THEN monitoring copy does get created in the database
        self.assertEqual(2, Monitoring.objects.all().count())

        # WHEN I get new monitoring and parameter
        copied_monitoring = Monitoring.objects.all().order_by('-id')[0]
        copied_parameter = Parameter.objects.all().order_by('-id')[0]

        # THEN monitorings fields should be equal
        # FIXME: modeltranslated fields doesn`t exist in post request
        # self.assertEqual(getattr(copied_monitoring, 'name_%s' % get_language()), 'monitoring name')
        self.assertEqual(copied_monitoring.status, PRE)

        # AND organizations names should be equal
        self.assertEqual(set(self.monitoring.organization_set.values_list('name', flat=True)),
                         set(copied_monitoring.organization_set.values_list('name', flat=True)))

        # AND all copied orgs have NTS status.
        statuses = copied_monitoring.organization_set.values_list('inv_status', flat=True)
        self.assertEqual(set(statuses), {'NTS', })

        # AND parameters name and code should be equal
        self.assertEqual(set(self.monitoring.parameter_set.values_list('name', 'code')),
                         set(copied_monitoring.parameter_set.values_list('name', 'code')))

        # AND scores fields should be equal
        fields = 'found complete topical accessible hypertext document image links recommendations revision'.split()
        self.assertEqual(
            set(self.parameter.score_set.values_list(*fields)),
            set(copied_parameter.score_set.values_list(*fields)))

        # AND there should be unseen orguser for the first organization
        org0_copy = copied_monitoring.organization_set.get(name=self.orgs[0].name)
        self.assertEqual(
            set(OrgUser.objects.values_list('userprofile_id', 'organization_id', 'seen')),
            {
                (self.orguser.profile.pk, self.orgs[0].pk, True),
                (self.orguser.profile.pk, org0_copy.pk, False)  # unseen
            })
