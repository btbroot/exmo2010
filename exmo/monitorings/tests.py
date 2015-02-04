# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2015 IRSI LTD
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
import datetime
import json
import unittest
from cStringIO import StringIO

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, Group, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.http import Http404
from django.test import TestCase
from django.utils.formats import get_format
from django.utils.translation import get_language
from mock import MagicMock, Mock
from model_mommy import mommy
from nose_parameterized import parameterized

from .forms import MonitoringCopyForm
from .views import monitorings_list, monitoring_organization_export
from core.utils import UnicodeReader
from core.test_utils import OptimizedTestCase
from custom_comments.models import CommentExmo
from exmo2010.models import (Claim, Monitoring, ObserversGroup, OpennessExpression,
                             Organization, Parameter, Task, Score, UserProfile)
from exmo2010.models.monitoring import INT, PRE, PUB


class MonitoringsAccessTestCase(OptimizedTestCase):
    # exmo2010:monitorings_list

    # Should always redirect anonymous to login page.
    # Should forbid get requests for non-experts.
    # Should forbid get requests with incorrect parameters for experts.
    # Should allow get requests with correct parameters for experts.

    @classmethod
    def setUpClass(cls):
        super(MonitoringsAccessTestCase, cls).setUpClass()

        cls.users = {}
        # GIVEN monitoring with organization
        cls.monitoring = mommy.make(Monitoring)
        organization = mommy.make(Organization, monitoring=cls.monitoring)
        # AND anonymous user
        cls.users['anonymous'] = AnonymousUser()
        # AND user without any permissions
        cls.users['user'] = User.objects.create_user('user', 'usr@svobodainfo.org', 'password')
        # AND superuser
        cls.users['admin'] = User.objects.create_superuser('admin', 'usr@svobodainfo.org', 'password')
        # AND expert B
        expertB = User.objects.create_user('expertB', 'usr@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        cls.users['expertB'] = expertB
        # AND expert A
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        cls.users['expertA'] = expertA
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'usr@svobodainfo.org', 'password')
        orguser.profile.organization = [organization]
        cls.users['orguser'] = orguser
        # AND translator
        translator = User.objects.create_user('translator', 'usr@svobodainfo.org', 'password')
        translator.profile.is_translator = True
        cls.users['translator'] = translator
        # AND observer user
        observer = User.objects.create_user('observer', 'usr@svobodainfo.org', 'password')
        # AND observers group for monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=cls.monitoring)
        obs_group.organizations = [organization]
        obs_group.users = [observer]
        cls.users['observer'] = observer
        # AND page url
        cls.url = reverse('exmo2010:monitorings_list')

    @parameterized.expand(zip(['GET', 'POST']))
    def test_redirect_anonymous(self, method, *args):
        # WHEN anonymous user send request to monitorings page
        request = MagicMock(user=self.users['anonymous'], method=method)
        request.get_full_path.return_value = self.url
        response = monitorings_list(request)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to login page
        self.assertEqual(response['Location'], '{}?next={}'.format(settings.LOGIN_URL, self.url))

    @parameterized.expand(zip(['orguser', 'translator', 'observer', 'user']))
    def test_forbid_get(self, username, *args):
        # WHEN authenticated user get monitorings page
        request = Mock(user=self.users[username], method='GET')
        # THEN response should raise PermissionDenied exception
        self.assertRaises(PermissionDenied, monitorings_list, request)

    @parameterized.expand(zip(['admin', 'expertA', 'expertB']))
    def test_allow_get(self, username, *args):
        # WHEN admin or any expert post get monitorings page
        request = MagicMock(user=self.users[username], method='GET')
        response = monitorings_list(request)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

    @parameterized.expand(zip(['unpublished', 'published']))
    def test_allow_get_with_params(self, param, *args):
        # WHEN admin or any expert post get monitorings page
        request = MagicMock(user=self.users['expertA'], method='GET')
        response = monitorings_list(request, param)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)


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


class MonitoringEditAccessTestCase(TestCase):
    # exmo2010:monitoring_update

    # TODO: move this testcase to *permissions* tests directory

    # Should allow only expertA to edit monitoring

    def setUp(self):
        # GIVEN monitoring with organization
        self.monitoring = mommy.make(Monitoring, name='initial', status=PRE)
        organization = mommy.make(Organization, monitoring=self.monitoring)

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

        self.url = reverse('exmo2010:monitoring_update', args=[self.monitoring.pk])

    def test_anonymous_monitoring_edit_get(self):
        # WHEN anonymous user gets monitoring edit page
        response = self.client.get(self.url, follow=True)
        # THEN he is redirected to login page
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + self.url)

    @parameterized.expand([
        ('user', 403),
        ('org', 403),
        ('expertB', 403),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_monitoring_edit_get(self, username, expected_response_code):
        self.client.login(username=username, password='password')

        # WHEN user gets monitoring edit page
        response = self.client.get(self.url)

        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand([
        ('user',),
        ('org',),
        ('expertB',),
    ])
    def test_forbid_unauthorized_monitoring_edit_post(self, username):
        self.client.login(username=username, password='password')

        input_format = get_format('DATE_INPUT_FORMATS')[0]
        now = datetime.datetime.now().strftime(input_format)

        # WHEN unauthorized user forges and POSTs monitoring edit form with changed name
        self.client.post(self.url, {
            'rate_date': now,
            'interact_date': now,
            'finishing_date': now,
            'publish_date': now,
            'openness_expression': 8,
            'status': PRE,
            'name': 'forged'})

        # THEN monitoring does not get changed in the database
        new_name = Monitoring.objects.get(pk=self.monitoring.pk).name
        self.assertEqual(self.monitoring.name, new_name)


class RatingsAverageTestCase(TestCase):
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


class ExpertARatingsTableVisibilityTestCase(TestCase):
    # exmo2010:ratings

    # TODO: move this testcase to *permissions* tests directory

    # On ratings page expert A should see only published monitorings (including hidden)

    def setUp(self):
        # GIVEN published monitoring
        self.mon_published = mommy.make(Monitoring, status=PUB)
        # AND published hidden monitoring
        self.mon_published_hidden = mommy.make(Monitoring, status=PUB, hidden=True)
        # AND interaction monitoring
        self.mon_interaction = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring
        self.mon_interaction_hidden = mommy.make(Monitoring, status=INT, hidden=True)

        # AND expert A account
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.groups.add(Group.objects.get(name=expertA.profile.expertA_group))

        # AND I logged in as expert A
        self.client.login(username='expertA', password='password')

    def test_visible_monitorings(self):
        # WHEN I get ratings page
        response = self.client.get(reverse('exmo2010:ratings'))
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND context should contain expected monitorings count
        expected_pks = {self.mon_published.pk, self.mon_published_hidden.pk}
        self.assertEqual(set(m.pk for m in response.context['monitoring_list']), expected_pks)


class ExpertBRatingsTableVisibilityTestCase(TestCase):
    # exmo2010:ratings

    # TODO: move this testcase to *permissions* tests directory

    # On ratings page expert B should see only published monitorings that are not hidden
    # and published monitorings with assigned tasks (hidden or not)

    def setUp(self):
        # GIVEN published monitoring
        self.mon_published = mommy.make(Monitoring, status=PUB)
        # AND published hidden monitoring
        self.mon_published_hidden = mommy.make(Monitoring, status=PUB, hidden=True)
        # AND published hidden monitoring with expert B task
        self.mon_published_hidden_with_task = mommy.make(Monitoring, status=PUB, hidden=True)
        # AND interaction monitoring
        self.mon_interaction = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring
        self.mon_interaction_hidden = mommy.make(Monitoring, status=INT, hidden=True)
        # AND interaction monitoring with expert B task
        self.mon_interaction_with_task = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring with expert B task
        self.mon_interaction_hidden_with_task = mommy.make(Monitoring, status=INT, hidden=True)
        # AND 1 organization in published hidden monitoring
        organization_1 = mommy.make(Organization, monitoring=self.mon_published_hidden_with_task)
        # AND 1 organization in interaction monitoring
        organization_2 = mommy.make(Organization, monitoring=self.mon_interaction_with_task)
        # AND 1 organization in interaction hidden monitoring
        organization_3 = mommy.make(Organization, monitoring=self.mon_interaction_hidden_with_task)

        # AND expert B account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.groups.add(Group.objects.get(name=expertB.profile.expertB_group))
        mommy.make(Task, organization=organization_1, user=expertB, status=Task.TASK_APPROVED)
        mommy.make(Task, organization=organization_2, user=expertB, status=Task.TASK_APPROVED)
        mommy.make(Task, organization=organization_3, user=expertB, status=Task.TASK_APPROVED)

        # AND I logged in as expert B
        self.client.login(username='expertB', password='password')

    def test_visible_monitorings(self):
        # WHEN I get ratings page
        response = self.client.get(reverse('exmo2010:ratings'))
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND context should contain expected monitorings count
        expected_pks = {self.mon_published.pk, self.mon_published_hidden_with_task.pk}
        self.assertEqual(set(m.pk for m in response.context['monitoring_list']), expected_pks)


class OrgUserRatingsTableVisibilityTestCase(TestCase):
    # exmo2010:ratings

    # TODO: move this testcase to *permissions* tests directory

    # On ratings page organization representative should see only
    # published monitorings and those with related organizations

    def setUp(self):
        # GIVEN published monitoring
        self.mon_published = mommy.make(Monitoring, status=PUB)
        # AND published hidden monitoring
        self.mon_published_hidden = mommy.make(Monitoring, status=PUB, hidden=True)
        # AND interaction monitoring
        self.mon_interaction = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring
        self.mon_interaction_hidden = mommy.make(Monitoring, status=INT, hidden=True)
        # AND interaction monitoring with representative
        self.mon_interaction_with_representative = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring with representative
        self.mon_interaction_hidden_with_representative = mommy.make(Monitoring, status=INT,
                                                                     hidden=True)
        # AND 1 organization in interaction monitoring with representative
        organization_1 = mommy.make(Organization, monitoring=self.mon_interaction_with_representative)
        # AND 1 organization in interaction hidden monitoring with representative
        organization_2 = mommy.make(Organization, monitoring=self.mon_interaction_hidden_with_representative)

        # AND organization representative account
        org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        org.groups.add(Group.objects.get(name=org.profile.organization_group))
        org.profile.organization = [organization_1, organization_2]

        # AND I logged in as organization representative
        self.client.login(username='org', password='password')

    def test_visible_monitorings(self):
        # WHEN I get ratings page
        response = self.client.get(reverse('exmo2010:ratings'))
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND context should contain expected monitorings count
        expected_pks = {self.mon_published.pk,
                        self.mon_interaction_with_representative.pk,
                        self.mon_interaction_hidden_with_representative.pk}
        self.assertEqual(set(m.pk for m in response.context['monitoring_list']), expected_pks)


class ObserversGroupRatingsTableVisibilityTestCase(TestCase):
    # exmo2010:ratings

    # TODO: move this testcase to *permissions* tests directory

    # On ratings page observers should see only
    # published monitorings and those with observed organizations

    def setUp(self):
        # GIVEN published monitoring
        self.mon_published = mommy.make(Monitoring, status=PUB)
        # AND published hidden monitoring
        self.mon_published_hidden = mommy.make(Monitoring, status=PUB, hidden=True)
        # AND interaction monitoring
        self.mon_interaction = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring
        self.mon_interaction_hidden = mommy.make(Monitoring, status=INT, hidden=True)
        # AND interaction monitoring with observed organizations
        self.mon_interaction_with_observed_orgs = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring with observed organizations
        self.mon_interaction_hidden_with_observed_orgs = mommy.make(Monitoring, status=INT, hidden=True)

        # AND 1 organization in interaction monitoring with observed organizations
        organization_1 = mommy.make(Organization, monitoring=self.mon_interaction_with_observed_orgs)
        # AND 1 organization in interaction hidden monitoring with observed organizations
        organization_2 = mommy.make(Organization, monitoring=self.mon_interaction_hidden_with_observed_orgs)

        # AND observer account
        observer = User.objects.create_user('observer', 'observer@svobodainfo.org', 'password')
        # AND observers group for interaction monitoring with observed organizations
        obs_group_1 = mommy.make(ObserversGroup, monitoring=self.mon_interaction_with_observed_orgs)
        obs_group_1.organizations = [organization_1]
        obs_group_1.users = [observer]
        # AND observers group for interaction hidden monitoring with observed organizations
        obs_group_2 = mommy.make(ObserversGroup, monitoring=self.mon_interaction_hidden_with_observed_orgs)
        obs_group_2.organizations = [organization_2]
        obs_group_2.users = [observer]

        # AND I logged in as observer
        self.client.login(username='observer', password='password')

    def test_visible_monitorings(self):
        # WHEN I get ratings page
        response = self.client.get(reverse('exmo2010:ratings'))
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND context should contain expected monitorings count
        expected_pks = {self.mon_published.pk,
                        self.mon_interaction_with_observed_orgs.pk,
                        self.mon_interaction_hidden_with_observed_orgs.pk}
        self.assertEqual(set(m.pk for m in response.context['monitoring_list']), expected_pks)


class AnonymousUserRatingsTableVisibilityTestCase(TestCase):
    # exmo2010:ratings

    # TODO: move this testcase to *permissions* tests directory

    # On ratings page anonymous and regular users should see only
    # published monitorings that are not hidden

    def setUp(self):
        # GIVEN published monitoring
        self.mon_published = mommy.make(Monitoring, status=PUB)
        # AND published hidden monitoring
        self.mon_published_hidden = mommy.make(Monitoring, status=PUB, hidden=True)
        # AND interaction monitoring
        self.mon_interaction = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring
        self.mon_interaction_hidden = mommy.make(Monitoring, status=INT, hidden=True)

    def test_visible_monitorings(self):
        # WHEN I get ratings page
        response = self.client.get(reverse('exmo2010:ratings'))
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND context should contain expected monitorings count
        expected_pks = {self.mon_published.pk}
        self.assertEqual(set(m.pk for m in response.context['monitoring_list']), expected_pks)


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
        cls.org_user.profile.organization = [org]

        # AND all users have all columns disabled in database.
        UserProfile.objects.update(**{
            'rt_initial_openness': False,
            'rt_final_openness': False,
            'rt_difference': False,
            'rt_representatives': False,
            'rt_comment_quantity': False
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
            'rt_comment_quantity': False
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
            'rt_comment_quantity': False
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
            'rt_initial_openness': False
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
        self.assertEqual(a['repr_len'], 0)
        self.assertEqual(a['active_repr_len'], 0)
        self.assertEqual(a['num_comments'], 0)
        self.assertEqual(a['openness'], 0)
        self.assertEqual(a['openness_initial'], 0)
        self.assertEqual(a['openness_delta'], 0.0)


class NameFilterRatingTestCase(TestCase):
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
    ''' Should count active and total organizations representatives on rating page '''

    def setUp(self):
        # GIVEN User instance and two connected organizations to it
        monitoring = mommy.make(Monitoring, status=PUB)
        monitoring_id = monitoring.pk
        organization1 = mommy.make(Organization, name='org1', monitoring=monitoring)
        organization2 = mommy.make(Organization, name='org2', monitoring=monitoring)
        self.url = reverse('exmo2010:monitoring_rating', args=[monitoring_id])
        self.usr = User.objects.create_user('usr', 'usr@svobodainfo.org', 'password')
        profile = self.usr.get_profile()
        profile.organization = [organization1, organization2]
        profile.save()
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

    def test_first_org_active_users(self):
        # WHEN representative adds a comment to first task's score
        comment = CommentExmo(content_type=self.content_type, object_pk=self.score1.pk, user=self.usr, site=self.site)
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
        comment = CommentExmo(content_type=self.content_type, object_pk=self.score2.pk, user=self.usr, site=self.site)
        comment.save()
        comment = CommentExmo(content_type=self.content_type, object_pk=self.score2.pk, user=self.usr, site=self.site)
        comment.save()

        # AND requests rating page for monitoring
        response = self.client.get(self.url)
        tasks = dict((t.organization.name, t) for t in response.context['rating_list'])
        t2 = tasks['org2']

        # THEN active representatives quantity for second organization equals 1
        self.assertEqual(t2.active_repr_len, 1)

    def test_non_existing_score_comments(self):
        # GIVEN comment to non-existing score
        comment = CommentExmo(content_type=self.content_type, object_pk=3, user=self.usr, site=self.site)
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
        self.assertEqual(representatives, "1 / 0")


class HiddenMonitoringVisibilityTestCase(TestCase):
    # exmo2010:ratings

    # TODO: move this testcase to *permissions* tests directory
    # TODO: split in few separate testcases for each view.

    def setUp(self):
        # GIVEN hidden and published monitoring
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
        profile.organization = [organization]

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



class TestMonitoringExport(TestCase):
    # Scenario: Экспорт данных мониторинга
    def setUp(self):
        # GIVEN предопределены все code OPENNESS_EXPRESSION
        for code in OpennessExpression.OPENNESS_EXPRESSIONS:
            # AND для каждого code есть опубликованный мониторинг
            monitoring = mommy.make(Monitoring, openness_expression__code=code, status=PUB)
            # AND в каждом мониторинге есть организация
            org = mommy.make(Organization, monitoring=monitoring)
            # AND есть активный пользователь, не суперюзер, expert (см выше, этот - не эксперт, надо создать эксперта)
            expert = mommy.make_recipe('exmo2010.active_user')
            expert.profile.is_expertB = True
            # AND в каждой организации есть одобренная задача для expert
            task = mommy.make(Task, organization=org, user=expert, status=Task.TASK_APPROVED,)
            # AND в каждом мониторинге есть параметр parameter с одним нерелевантным критерием
            parameter = mommy.make(Parameter, monitoring=monitoring, complete=False, weight=1)
            # AND в каждой задаче есть две ревизии оценки по parameter
            score = mommy.make(Score, task=task, parameter=parameter)
            score = mommy.make(Score, task=task, parameter=parameter, revision=Score.REVISION_INTERACT)

    def parameter_type(self, score):
        return 'npa' if score.parameter.npa else 'other'

    @parameterized.expand(
        [("expression-v%d" % code, code)
            for code in OpennessExpression.OPENNESS_EXPRESSIONS])
    def test_json(self, name, code):
        monitoring = Monitoring.objects.get(openness_expression__code=code)
        # WHEN анонимный пользователь запрашивает данные каждого мониторинга в json
        url = reverse('exmo2010:monitoring_export', args=[monitoring.pk])
        response = self.client.get(url + '?format=json')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается json
        self.assertEqual(response.get('content-type'), 'application/json')
        json_file = json.loads(response.content)
        organization = monitoring.organization_set.all()[0]
        task = organization.task_set.all()[0]
        score = task.score_set.filter(revision=Score.REVISION_DEFAULT,)[0]
        # AND имя мониторинга в БД и json совпадает
        self.assertEqual(json_file['monitoring']['name'], monitoring.name)
        # AND имя организации (для первой задачи) в БД и json совпадает
        self.assertEqual(
            json_file['monitoring']['tasks'][0]['name'],
            organization.name)
        # AND КИД (для первой задачи) в БД и json совпадает
        self.assertEqual(
            json_file['monitoring']['tasks'][0]['openness'],
            ('%.3f' % task.openness) if task.openness is not None else task.openness)
        self.assertEqual(
            int(json_file['monitoring']['tasks'][0]['position']),
            1)
        # AND балл найденности (в первой задаче, в оценке по первому параметру)
        # в БД и json совпадает
        self.assertEqual(
            int(json_file['monitoring']['tasks'][0]['scores'][0]['found']),
            int(score.found))
        self.assertEqual(
            json_file['monitoring']['tasks'][0]['scores'][0]['type'],
            self.parameter_type(score)
        )

    @parameterized.expand(
        [("expression-v%d" % code, code)
            for code in OpennessExpression.OPENNESS_EXPRESSIONS])
    def test_csv(self, name, code):
        monitoring = Monitoring.objects.get(openness_expression__code=code)
        # WHEN анонимный пользователь запрашивает данные каждого мониторинга в csv
        url = reverse('exmo2010:monitoring_export', args=[monitoring.pk])
        response = self.client.get(url + '?format=csv')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается csv
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        csv = UnicodeReader(StringIO(response.content))
        organization = monitoring.organization_set.all()[0]
        task = organization.task_set.all()[0]
        row_count = 0
        for row in csv:
            row_count += 1
            if row_count == 1:
                self.assertEqual(row[0], '#Monitoring')
                continue
            else:
                if row[0].startswith('#'):
                    continue
                self.assertEqual(len(row), 18)
                revision = row[17]
                self.assertIn(revision, Score.REVISION_EXPORT.values())
                for k, v in Score.REVISION_EXPORT.iteritems():
                    if v == revision:
                        revision = k
                        break
                score = task.score_set.filter(revision=revision)[0]
                # AND имя мониторинга в БД и json совпадает
                self.assertEqual(row[0], monitoring.name)
                # AND имя организации (для первой задачи) в БД и json совпадает
                self.assertEqual(
                    row[1],
                    organization.name)
                self.assertEqual(
                    int(row[2]),
                    organization.pk)
                self.assertEqual(
                    int(row[3]),
                    1)
                # AND КИД (для первой задачи) в БД и json совпадает
                self.assertEqual(
                    row[5],
                    '%.3f' % task.openness if task.openness is not None else '')
                self.assertEqual(
                    float(row[7]),
                    float(score.parameter.pk))
                # AND балл найденности (в первой задаче, в оценке по первому параметру)
                # в БД и json совпадает
                self.assertEqual(
                    int(row[8]),
                    int(score.found))
                self.assertEqual(
                    row[16],
                    self.parameter_type(score)
                )


class TestMonitoringExportApproved(TestCase):
    # Scenario: Экспорт данных мониторинга
    def setUp(self):
        # GIVEN published monitoring with 1 organization
        self.monitoring = mommy.make(Monitoring, status=PUB)
        organization = mommy.make(Organization, monitoring=self.monitoring)
        # AND 2 experts B
        expertB_1 = User.objects.create_user('expertB_1', 'expertB_1@svobodainfo.org', 'password')
        expertB_1.profile.is_expertB = True
        expertB_2 = User.objects.create_user('expertB_2', 'expertB_2@svobodainfo.org', 'password')
        expertB_2.profile.is_expertB = True
        # AND approved task assigned to expertB_1
        approved_task = mommy.make(
            Task,
            organization=organization,
            user=expertB_1,
            status=Task.TASK_APPROVED,
        )
        # AND open task assigned to expertB_2
        open_task = mommy.make(
            Task,
            organization=organization,
            user=expertB_2,
            status=Task.TASK_OPEN,
        )
        # AND 1 parameter
        parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        # AND 1 score for each task
        mommy.make(Score, task=approved_task, parameter=parameter)
        mommy.make(Score, task=open_task, parameter=parameter)

    def test_approved_json(self):
        url = reverse('exmo2010:monitoring_export', args=[self.monitoring.pk])
        response = self.client.get(url + '?format=json')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается json
        self.assertEqual(response.get('content-type'), 'application/json')
        json_file = json.loads(response.content)
        self.assertEqual(len(json_file['monitoring']['tasks']), 1, json.dumps(json_file, indent=2))

    # FIXME: не работает в автотестах перед пушем в мастер.
    # По какой-то причине в csv присутствует еще и первоначальная оценка.
    # Traceback (most recent call last):
    #   File "/tmp/exmo_test_repo/exmo/monitorings/tests.py", line 888, in test_approved_csv
    #     self.assertEqual(len(csv), 3)
    # AssertionError: 4 != 3
    @unittest.skipIf(not settings.DEBUG, 'Git hook with autotests return AssertionError')
    def test_approved_csv(self):
        url = reverse('exmo2010:monitoring_export', args=[self.monitoring.pk])
        response = self.client.get(url + '?format=csv')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается csv
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        csv = [line for line in UnicodeReader(StringIO(response.content))]
        # only header, 1 string of content and license
        self.assertEqual(len(csv), 3)


class OrganizationExportAccessTestCase(OptimizedTestCase):
    # exmo2010:monitoring_organization_export

    # Should allow experts A and superusers download csv-file.
    # Should redirect anonymous to login page.
    # Should forbid all other users to download csv-file.

    @classmethod
    def setUpClass(cls):
        super(OrganizationExportAccessTestCase, cls).setUpClass()

        cls.users = {}
        # GIVEN monitoring with organization
        cls.monitoring = mommy.make(Monitoring)
        organization = mommy.make(Organization, monitoring=cls.monitoring)
        # AND anonymous user
        cls.users['anonymous'] = AnonymousUser()
        # AND user without any permissions
        cls.users['user'] = User.objects.create_user('user', 'usr@svobodainfo.org', 'password')
        # AND superuser
        cls.users['admin'] = User.objects.create_superuser('admin', 'usr@svobodainfo.org', 'password')
        # AND expert B
        expertB = User.objects.create_user('expertB', 'usr@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        cls.users['expertB'] = expertB
        # AND expert A
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        cls.users['expertA'] = expertA
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'usr@svobodainfo.org', 'password')
        orguser.profile.organization = [organization]
        cls.users['orguser'] = orguser
        # AND translator
        translator = User.objects.create_user('translator', 'usr@svobodainfo.org', 'password')
        translator.profile.is_translator = True
        cls.users['translator'] = translator
        # AND observer user
        observer = User.objects.create_user('observer', 'usr@svobodainfo.org', 'password')
        # AND observers group for monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=cls.monitoring)
        obs_group.organizations = [organization]
        obs_group.users = [observer]
        cls.users['observer'] = observer
        # AND url
        cls.url = reverse('exmo2010:monitoring_organization_export', args=[cls.monitoring.pk])

    @parameterized.expand(zip(['admin', 'expertA']))
    def test_allow_csv(self, username, *args):
        # WHEN privileged user download file
        request = Mock(user=self.users[username], method='GET')
        response = monitoring_organization_export(request, self.monitoring.pk)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

    @parameterized.expand(zip(['expertB', 'orguser', 'translator', 'observer', 'user']))
    def test_forbid_csv(self, username, *args):
        # WHEN authenticated user without permissions download file
        request = Mock(user=self.users[username], method='GET')
        # THEN response should raise PermissionDenied exception
        self.assertRaises(PermissionDenied, monitoring_organization_export, request, self.monitoring.pk)

    def test_redirect_anonymous(self):
        # WHEN anonymous user download file
        request = MagicMock(user=self.users['anonymous'], method='GET')
        request.get_full_path.return_value = self.url
        response = monitoring_organization_export(request, self.monitoring.pk)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to login page
        self.assertEqual(response['Location'], '{}?next={}'.format(settings.LOGIN_URL, self.url))


class OrganizationExportTestCase(TestCase):
    # exmo2010:monitoring_organization_export

    # Organizations export response should contain properly generated csv-file content.

    def setUp(self):
        # GIVEN published monitoring with 1 organization
        monitoring = mommy.make(Monitoring)
        # AND organization with email, url and phone
        self.org = mommy.make(Organization, monitoring=monitoring,
                              email='org@test.com', url='http://org.ru', phone='1234567')
        # AND expert A account
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND organization export url
        self.url = reverse('exmo2010:monitoring_organization_export', args=[monitoring.pk])

    def test_organization_csv(self):
        # WHEN I am logged in as expert A
        self.client.login(username='expertA', password='password')
        # AND download csv
        hostname = 'test.host.com'
        response = self.client.get(self.url, HTTP_HOST=hostname)
        # THEN status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND file should be csv-file
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        csv = [line for line in UnicodeReader(StringIO(response.content))]
        # AND file should contain 3 lines (header, 1 string of content and license)
        self.assertEqual(len(csv), 3)
        for row in csv:
            if not row[0].startswith('#'):
                # AND length of content line should equal 6
                self.assertEqual(len(row), 6)
                org_data = [
                    self.org.name,
                    self.org.url,
                    self.org.email,
                    self.org.phone,
                    self.org.inv_code,
                    'http://' + hostname + reverse('exmo2010:auth_orguser') + '?code={}'.format(self.org.inv_code)
                ]
                # AND content should describe existing organization
                self.assertEqual(row, org_data)


class UploadParametersCSVTest(TestCase):
    # Upload parameters.

    def setUp(self):
        # GIVEN interaction monitoring
        self.monitoring = mommy.make(Monitoring, status=INT)
        # AND expert A account
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True
        # AND url for csv-file importing
        self.url = reverse('exmo2010:monitoring_parameter_import', args=[self.monitoring.pk])
        # AND I am logged in as expert A
        self.client.login(username='expertA', password='password')

    def test_empty_name_param_upload(self):
        csv_data = unicode(
            # code,name,grounds,rating_procedure,notes,complete,topical,accessible,hypertext,document,image,weight
            '1,name1,grounds1,,,1,1,1,1,0,0,3\n'
            '2,name2,,rating_procedure2,notes2,1,1,1,1,0,0,3\n'
            '3,\n'   # incomplete row
            '4,name4,grounds4,rating_procedure4,notes4,1,1,1,1,0,0,3')
        f = ContentFile(csv_data.encode('utf-16'), name='temp.csv')

        # WHEN I upload csv file with incomplete third row, missing name and all columns after
        response = self.client.post(self.url, data={'paramfile': f, 'monitoring_pk': self.monitoring.pk})
        # THEN response should display error in third line
        self.assertEqual(response.context['errors'], ['row 3 (csv). Empty name'])


class TranslatedMonitoringScoresDataExportTestCase(TestCase):
    # Should export content in a different languages

    def setUp(self):
        # GIVEN published monitoring with 1 organization
        self.monitoring = mommy.make(Monitoring, status=PUB, name_en='monitoring', name_ru=u'мониторинг')
        self.organization = mommy.make(Organization, monitoring=self.monitoring, name_en='organization', name_ru=u'организация')
        # AND expert B account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND 2 users accounts with different languages
        user_en = User.objects.create_user('user_en', 'en_user@svobodainfo.org', 'password')
        user_en.profile.language = 'en'
        user_en.profile.save()
        user_ru = User.objects.create_user('user_ru', 'ru_user@svobodainfo.org', 'password')
        user_ru.profile.language = 'ru'
        user_ru.profile.save()
        # AND approved task assigned to expert B
        task = mommy.make(Task, organization=self.organization, user=expertB, status=Task.TASK_APPROVED,)
        # AND 1 parameter
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1, name_en='parameter', name_ru=u'параметр')
        # AND 2 scores
        mommy.make(Score, task=task, parameter=self.parameter)
        mommy.make(Score, task=task, parameter=self.parameter, revision=Score.REVISION_INTERACT)
        self.url = reverse('exmo2010:monitoring_export', args=[self.monitoring.pk])

    @parameterized.expand([
        ('ru',),
        ('en',),
    ])
    def test_json(self, lang):
        # WHEN I am logged in as user
        self.client.login(username='user_%s' % lang, password='password')
        # AND I get json-file from response for current monitoring
        response = self.client.get(self.url + '?format=json', follow=True)
        json_file = json.loads(response.content)
        # THEN monitoring, organization and parameter names should be in user preferable language
        field = 'name_%s' % lang
        self.assertEqual(json_file['monitoring']['name'], getattr(self.monitoring, field))
        self.assertEqual(json_file['monitoring']['tasks'][0]['name'], getattr(self.organization, field))
        self.assertEqual(json_file['monitoring']['tasks'][0]['scores'][0]['name'], getattr(self.parameter, field))

    @parameterized.expand([
        ('ru',),
        ('en',),
    ])
    def test_csv(self, lang):
        # WHEN I am logged in as user
        self.client.login(username='user_%s' % lang, password='password')
        # AND I get csv-file from response for current monitoring
        response = self.client.get(self.url + '?format=csv', follow=True)
        csv = UnicodeReader(StringIO(response.content))
        field = 'name_%s' % lang
        for count, row in enumerate(csv, 1):
            if count != 1 and not row[0].startswith('#'):
                # THEN monitoring, organization and parameter names should be in user preferable language
                self.assertEqual(row[0], getattr(self.monitoring, field))
                self.assertEqual(row[1], getattr(self.organization, field))
                self.assertEqual(row[6], getattr(self.parameter, field))


class OrgUserRatingAccessTestCase(TestCase):
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
        user.profile.organization = [organization]
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
        self.parameters = mommy.make(Parameter, monitoring=self.monitoring, weight=1, exclude=None, _quantity=2,
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


class SuperuserRatingOrgsVisibilityTestCase(TestCase):
    # exmo2010:monitoring_rating

    # TODO: move this testcase into *permissions* tests directory

    # Superuser should see all organizations on rating page

    def setUp(self):
        # GIVEN interaction monitoring
        self.monitoring = mommy.make(Monitoring, status=INT)
        # AND 2 organizations connected to monitoring
        organization1 = mommy.make(Organization, name='org1', monitoring=self.monitoring)
        organization2 = mommy.make(Organization, name='org2', monitoring=self.monitoring)
        # AND 2 approved tasks connected to organizations
        self.task1 = mommy.make(Task, organization=organization1, status=Task.TASK_APPROVED)
        self.task2 = mommy.make(Task, organization=organization2, status=Task.TASK_APPROVED)
        # AND parameter connected to monitoring
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        # AND 1 score for each task
        mommy.make(Score, task=self.task1, parameter=self.parameter)
        mommy.make(Score, task=self.task2, parameter=self.parameter)
        # AND superuser account
        User.objects.create_superuser('admin', 'admin@svobodainfo.org', 'password')
        # AND monitoring rating page url
        self.url = reverse('exmo2010:monitoring_rating', args=[self.monitoring.pk])
        # AND I am logged in as superuser
        self.client.login(username='admin', password='password')

    def test_rating_list(self):
        # WHEN I get rating page
        response = self.client.get(self.url)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND count of approved tasks should be 2
        self.assertEqual(len(response.context['rating_list']), 2)


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
        self.orguser1.profile.organization = [organization1]
        # AND one more organization representative connected to both organizations
        self.orguser2 = User.objects.create_user('org2', 'org@svobodainfo.org', 'password')
        self.orguser2.groups.add(Group.objects.get(name=self.orguser2.profile.organization_group))
        self.orguser2.profile.organization = [organization1, organization2]
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


class MonitoringCopyAccessTestCase(TestCase):
    # exmo2010:monitoring_copy

    # TODO: move this testcase into *permissions* tests directory

    # Should allow only expertA to copy monitoring

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND organization
        organization = mommy.make(Organization, monitoring=self.monitoring)
        # AND superuser account
        User.objects.create_superuser('admin', 'usr@svobodainfo.org', 'password')
        # AND expert A account
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND expert B account
        expertB = User.objects.create_user('expertB', 'usr@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'usr@svobodainfo.org', 'password')
        orguser.profile.organization = [organization]
        # AND user without any permissions
        User.objects.create_user('user', 'usr@svobodainfo.org', 'password')
        # AND monitoring copy page url
        self.url = reverse('exmo2010:monitoring_copy', args=[self.monitoring.pk])

    def test_anonymous_monitoring_copy_get(self):
        # WHEN anonymous user gets monitoring copy page
        response = self.client.get(self.url, follow=True)
        # THEN he is redirected to login page
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + self.url)

    @parameterized.expand([
        ('user', 403),
        ('orguser', 403),
        ('expertB', 403),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_monitoring_copy_get(self, username, expected_response_code):
        # WHEN I am logged in
        self.client.login(username=username, password='password')
        # AND I get monitoring copy page
        response = self.client.get(self.url)
        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand([
        ('user',),
        ('orguser',),
        ('expertB',),
    ])
    def test_forbid_unauthorized_monitoring_copy_post(self, username):
        # WHEN I am logged in
        self.client.login(username=username, password='password')

        now = datetime.datetime.now().strftime(get_format('DATE_INPUT_FORMATS')[0])

        # AND I forge and POST monitoring copy form
        self.client.post(self.url, {
            'name_%s' % get_language(): 'monitoring name',
            'status': PRE,
            'openness_expression': 8,
            'donors': ['all'],
            'rate_date': now,
            'interact_date': now,
            'finishing_date': now,
            'publish_date': now,
        })
        # THEN monitoring copy does not get created in the database
        self.assertEqual(1, Monitoring.objects.all().count())


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


class CopyMonitoringViewTestCase(TestCase):
    # exmo2010:monitoring_copy

    # TODO: move this testcase into *general logic* tests directory

    # monitoring copy should be created

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND 3 organizations connected to monitoring
        orgs = mommy.make(Organization, monitoring=self.monitoring, _quantity=3)
        # AND parameter connected to monitoring
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring)
        # AND expert A account
        self.expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True
        # AND expert B account
        self.expertB = User.objects.create_user('expertB', 'usr@svobodainfo.org', 'password')
        self.expertB.profile.is_expertB = True
        # AND 3 approved tasks connected to organizations
        task1 = mommy.make(Task, organization=orgs[0], user=self.expertB, status=Task.TASK_APPROVED)
        task2 = mommy.make(Task, organization=orgs[1], user=self.expertB, status=Task.TASK_APPROVED)
        task3 = mommy.make(Task, organization=orgs[2], user=self.expertB, status=Task.TASK_APPROVED)
        # AND 1 score for each task
        mommy.make(Score, task=task1, parameter=self.parameter)
        mommy.make(Score, task=task2, parameter=self.parameter)
        mommy.make(Score, task=task3, parameter=self.parameter)
        # AND monitoring copy page url
        self.url = reverse('exmo2010:monitoring_copy', args=[self.monitoring.pk])
        # WHEN I am logged in as expert A
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
        # FIXME: modeltranslated fields doesn`t exists in post request
        # self.assertEqual(getattr(copied_monitoring, 'name_%s' % get_language()), 'monitoring name')
        self.assertEqual(copied_monitoring.status, PRE)
        # AND organizations names should be equal
        self.assertEqual(set(self.monitoring.organization_set.values_list('name', flat=True)),
                         set(copied_monitoring.organization_set.values_list('name', flat=True)))
        # AND parameters name and code should be equal
        self.assertEqual(set(self.monitoring.parameter_set.values_list('name', 'code')),
                         set(copied_monitoring.parameter_set.values_list('name', 'code')))
        # AND scores fields should be equal
        fields = 'found complete topical accessible hypertext document image links recommendations revision'.split()
        self.assertEqual(
            set(self.parameter.score_set.values_list(*fields)),
            set(copied_parameter.score_set.values_list(*fields)))
