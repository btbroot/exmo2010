# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Foundation "Institute for Information Freedom Development"
# Copyright 2013 Al Nikolov
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
import urllib
from cStringIO import StringIO

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpRequest, Http404
from django.test import TestCase
from django.test.client import Client
from django.utils import simplejson
from django.utils.formats import get_format
from django.utils.translation import ungettext
from model_mommy import mommy
from nose_parameterized import parameterized
from BeautifulSoup import BeautifulSoup

from core.utils import UnicodeReader
from custom_comments.models import CommentExmo
from exmo2010.models import *


class MonitoringEditAccessTestCase(TestCase):
    # SHOULD allow only expertA to edit monitoring

    def setUp(self):
        self.client = Client()
        # GIVEN monitoring with organization and openness_expression
        #openness_expression = mommy.make(OpennessExpression, openness_expression)
        self.monitoring = mommy.make(Monitoring, name='initial', status=MONITORING_PREPARE)
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
        response = self.client.get(self.url)
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
            'status': MONITORING_PREPARE,
            'name': 'forged'})

        # THEN monitoring does not get changed in the database
        new_name = Monitoring.objects.get(pk=self.monitoring.pk).name
        self.assertEqual(self.monitoring.name, new_name)


class RatingsTableValuesTestCase(TestCase):
    # Scenario: Output to Ratings Table
    def setUp(self):
        # GIVEN published monitoring with a particular
        # name and published date
        self.client = Client()
        self.today = datetime.date.today()
        self.monitoring_name = "Name"
        monitoring = mommy.make(
            Monitoring,
            status=MONITORING_PUBLISHED,
            name=self.monitoring_name,
            publish_date=self.today
        )
        # AND one organization connected to monitoring
        organization = mommy.make(Organization, monitoring=monitoring)
        task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)

        # AND parameter with zero weight
        parameter = mommy.make(Parameter, monitoring=monitoring, weight=0)

        # AND score of this parameter
        score = mommy.make(Score, task=task, parameter=parameter)

    def test_values(self):
        # WHEN user requests ratings page
        response = self.client.get(reverse('exmo2010:ratings'))
        monitoring = response.context['monitoring_list'][0]
        # THEN server returns "OK" response
        self.assertEqual(response.status_code, 200)

        # AND output name equals initial name
        self.assertEqual(monitoring.name, self.monitoring_name)

        # AND output date equals initial date
        self.assertEqual(monitoring.publish_date, self.today)

        # AND output quantity of organizations equals one
        self.assertEqual(monitoring.org_count, 1)

        # AND average openness is None because all parameters weight is 0
        self.assertEqual(monitoring.average, None)


class RatingTableColumnOptionsTestCase(TestCase):
    # SHOULD display only permitted rating table columns for users
    # AND allow to choose displayed columns for registered users and remember that choice

    rt_fields_nonexpert = ['rt_initial_openness', 'rt_final_openness', 'rt_difference']
    rt_fields_all = rt_fields_nonexpert + ['rt_representatives', 'rt_comment_quantity']

    def setUp(self):
        self.client = Client()
        # GIVEN expert and regular nonexpert user
        self.expertA = User.objects.create_user('expert', 'usr@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True
        self.user = User.objects.create_user('nonexpert', 'usr@svobodainfo.org', 'password')
        # AND a Score for a Parameter in an APPROVED Task for an Organization in a PUBLISHED Monitoring
        self.monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        organization = mommy.make(Organization, monitoring=self.monitoring)
        parameter = mommy.make(Parameter, monitoring=self.monitoring)
        task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)
        mommy.make(Score, task=task, parameter=parameter)

        # AND default options values for each user
        self.default_options = {
            'expert': {
                'rt_initial_openness': False,
                'rt_final_openness': True,
                'rt_difference': True,
                'rt_representatives': True,
                'rt_comment_quantity': True
            },
            'nonexpert': {
                'rt_initial_openness': False,
                'rt_final_openness': True,
                'rt_difference': True,
            }
        }

    def profile_fields(self, username, fields):
        ''' Get dictionary of field-value from UserProfile for given user '''
        return UserProfile.objects.filter(user__username=username).values(*fields)[0]

    def get_response_columns_options(self, *args):
        ''' Get dictionary of rt_* field values from response to rating_url with given *args (GET params) '''
        rating_url = reverse('exmo2010:monitoring_rating', args=[self.monitoring.pk])
        response = self.client.get(rating_url, *args)
        columns_form = response.context['rating_columns_form']
        return {f: bool(columns_form[f].value()) for f in columns_form.fields}

    @parameterized.expand([
        ('nonexpert', rt_fields_nonexpert),
        ('expert', rt_fields_all),
    ])
    def test_rt_columns_default(self, username, fields):
        # WHEN User just created
        # THEN default options are stored in user's profile
        self.assertEqual(self.default_options[username], self.profile_fields(username, fields))

        # WHEN User logs in
        self.client.login(username=username, password='password')

        # AND requests rating page without GET parameters
        columns_options = self.get_response_columns_options()

        # THEN default columns are displayed (columns_form values are equal defaults)
        self.assertEqual(columns_options, self.default_options[username])

        # AND default options are still stored in user's profile
        self.assertEqual(self.default_options[username], self.profile_fields(username, fields))

    @parameterized.expand([
        ('nonexpert', rt_fields_nonexpert),
        ('expert', rt_fields_all),
    ])
    def test_rt_columns_store(self, username, fields):
        # WHEN User logs in
        self.client.login(username=username, password='password')

        # AND user requests rating page with only rt_final_openness column (GET parameter "on")
        changed_options = self.get_response_columns_options({'rt_final_openness': 'on'})

        # THEN only rt_final_openness column is displayed (only this value is True in columns_form)
        expected = {f: False for f in fields}
        expected['rt_final_openness'] = True
        self.assertEqual(changed_options, expected)

        # AND changes are stored in user's profile
        self.assertEqual(changed_options, self.profile_fields(username, fields))

        # WHEN user requests rating page again, but without GET parameters
        requested_again_options = self.get_response_columns_options()

        # THEN only columns that was saved before as enabled are displayed (only rt_final_openness)
        self.assertEqual(requested_again_options, changed_options)

        # AND previously changed options are still stored in user's profile
        self.assertEqual(changed_options, self.profile_fields(username, fields))

    def test_rt_columns_nonexpert_forbidden(self):
        # WHEN user logs in
        self.client.login(username='nonexpert', password='password')

        # AND user requests rating page with forbidden rt_representatives column (GET parameter "on")
        forbidden_options = self.get_response_columns_options({'rt_representatives': 'on'})

        # THEN default columns are displayed, and forbidden column is not
        self.assertEqual(forbidden_options, self.default_options['nonexpert'])

    def test_rt_columns_anonymous(self):
        # WHEN AnonymousUser requests rating page without GET parameters
        columns_options = self.get_response_columns_options()

        # THEN default columns are displayed
        self.assertEqual(columns_options, self.default_options['nonexpert'])


class RatingTableValuesTestCase(TestCase):
    # Scenario: Output to Rating Table
    def setUp(self):
        # GIVEN published monitoring
        self.client = Client()
        self.monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        self.monitoring_id = self.monitoring.pk
        self.url = reverse('exmo2010:monitoring_rating', args=[self.monitoring_id])
        organization = mommy.make(Organization, monitoring=self.monitoring)
        self.task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        score = mommy.make(Score, task=self.task, parameter=self.parameter, found=0)

    def test_rt_row_output(self):
        # WHEN user requests rating page
        response = self.client.get(self.url)
        o = response.context['rating_list'][0]
        # THEN output data equals default values for organization
        self.assertEqual(o, self.task)
        self.assertEqual(o.place, 1)
        self.assertEqual(o.repr_len, 0)
        self.assertEqual(o.active_repr_len, 0)
        self.assertEqual(o.comments, 0)
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
        self.assertEqual(a['comments'], 0)
        self.assertEqual(a['openness'], 0)
        self.assertEqual(a['openness_initial'], 0)
        self.assertEqual(a['openness_delta'], 0.0)


class NameFilterRatingTestCase(TestCase):
    ''' If name filter given on rating page, should show only filtered orgs '''

    def setUp(self):
        self.client = Client()

        # GIVEN monitoring with 2 organizations
        monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        monitoring_id = monitoring.pk
        organization1 = mommy.make(Organization, name='org1', monitoring=monitoring)
        organization2 = mommy.make(Organization, name='org2', monitoring=monitoring)

        # AND two corresponding tasks, parameters, and scores for organizations
        task1 = mommy.make(Task, organization=organization1, status=Task.TASK_APPROVED)
        task2 = mommy.make(Task, organization=organization2, status=Task.TASK_APPROVED)
        parameter1 = mommy.make(Parameter, monitoring=monitoring, weight=1)
        parameter2 = mommy.make(Parameter, monitoring=monitoring, weight=1)
        score1 = mommy.make(Score, task=task1, parameter=parameter1)
        score2 = mommy.make(Score, task=task2, parameter=parameter2)

        self.url = reverse('exmo2010:monitoring_rating', args=[monitoring_id])

    @parameterized.expand([
        ('org1', ['org1']),
        ('org', ['org1', 'org2']),
        ('qwe', []),
    ])
    def test_org_filter(self, filter_str, expected_org_names):
        # WHEN user requests rating page with name_filter
        response = self.client.get(self.url, {'name_filter': filter_str})

        # THEN only expected orgs should be shown
        org_names = set(t.organization.name for t in response.context['rating_list'])
        self.assertEqual(set(expected_org_names), org_names)


class RatingActiveRepresentativesTestCase(TestCase):
    ''' Should count active and total organizations representatives on rating page '''

    def setUp(self):
        # GIVEN User instance and two connected organizations to it
        self.client = Client()
        monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
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
    def setUp(self):
        # GIVEN hidden and published monitoring
        self.client = Client()
        self.url = reverse('exmo2010:ratings')
        self.monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED, hidden=True)
        self.monitoring_id = self.monitoring.pk

        # AND organization connected to monitoring
        organization = mommy.make(Organization, monitoring=self.monitoring)

        # AND expertB connected to organization
        self.expertB = User.objects.create_user('expertB', 'expertb@svobodainfo.org', 'password')
        self.expertB.groups.add(Group.objects.get(name=self.expertB.profile.expertB_group))

        # AND representative connected to organization
        self.org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        self.org.groups.add(Group.objects.get(name=self.org.profile.organization_group))
        profile = self.org.get_profile()
        profile.organization = [organization]

        # AND expertA
        self.expertA = User.objects.create_user('expertA', 'experta@svobodainfo.org', 'password')
        self.expertA.groups.add(Group.objects.get(name=self.expertA.profile.expertA_group))

        # AND superuser
        self.su = User.objects.create_superuser('su', 'su@svobodainfo.org', 'password')

        # AND task, parameter and score
        task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED, user=self.expertB)
        parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        self.score = mommy.make(Score, task=task, parameter=parameter)

        # AND regular user
        self.usr = User.objects.create_user('usr', 'usr@svobodainfo.org', 'password')

        # AND expertB not connected to task
        self.expertB_out = User.objects.create_user('expertB_out', 'expertb.out@svobodainfo.org', 'password')
        self.expertB_out.groups.add(Group.objects.get(name=self.expertB_out.profile.expertB_group))

        # AND organization representative not connected to task
        self.org_out = User.objects.create_user('org_out', 'org.out@svobodainfo.org', 'password')
        self.org_out.groups.add(Group.objects.get(name=self.org_out.profile.organization_group))

    @parameterized.expand([
        ('expertB',),
        ('org',),
        ('expertA',),
        ('su',),
    ])
    def test_allowed_users_see_monitoring(self, username):
        # WHEN user logging in
        self.client.login(username=username, password='password')
        # AND requests ratings page
        response = self.client.get(self.url)
        response_monitoring = response.context['monitoring_list'][0]
        # THEN response's context contains hidden monitoring in monitoring list
        # for connected organization representative, connected expertB, expertA and superuser
        self.assertEqual(response_monitoring, self.monitoring)

    @parameterized.expand([
        (None,),
        ('usr',),
        ('expertB_out',),
        ('org_out',),
    ])
    def test_forbidden_users_do_not_see_monitoring(self, username):
        # WHEN user logging in
        self.client.login(username=username, password='password')
        # AND requests ratings page
        response = self.client.get(self.url)
        response_monitoring_list = response.context['monitoring_list']
        # THEN response's context contains no monitoring in monitoring list
        # for disconnected organization representative, disconnected expertB, anonymous and regular user
        self.assertEqual(len(response_monitoring_list), 0)


class EmptyMonitoringRatingTestCase(TestCase):
    def setUp(self):
        # GIVEN monitoring without tasks
        self.client = Client()
        self.monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        self.monitoring_id = self.monitoring.pk
        self.url = reverse('exmo2010:monitoring_rating', args=[self.monitoring_id])
        organization = mommy.make(Organization, monitoring=self.monitoring)
        # AND expertA account
        self.usr = User.objects.create_user('usr', 'usr@svobodainfo.org', 'password')
        self.usr.groups.add(Group.objects.get(name=self.usr.profile.expertA_group))

    def test_ok_response(self):
        self.client.login(username='usr', password='password')
        # WHEN expertA requests rating page
        response = self.client.get(self.url)
        # THEN server's response is OK
        self.assertEqual(response.status_code, 200)


class TestMonitoringExport(TestCase):
    # Scenario: Экспорт данных мониторинга
    def setUp(self):
        self.client = Client()
        # GIVEN предопределены все code OPENNESS_EXPRESSION
        for code in OpennessExpression.OPENNESS_EXPRESSIONS:
            # AND для каждого code есть опубликованный мониторинг
            monitoring = mommy.make(Monitoring, openness_expression__code=code, status=MONITORING_PUBLISHED)
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
        json = simplejson.loads(response.content)
        organization = monitoring.organization_set.all()[0]
        task = organization.task_set.all()[0]
        score = task.score_set.filter(revision=Score.REVISION_DEFAULT,)[0]
        # AND имя мониторинга в БД и json совпадает
        self.assertEqual(json['monitoring']['name'], monitoring.name)
        # AND имя организации (для первой задачи) в БД и json совпадает
        self.assertEqual(
            json['monitoring']['tasks'][0]['name'],
            organization.name)
        # AND КИД (для первой задачи) в БД и json совпадает
        self.assertEqual(
            json['monitoring']['tasks'][0]['openness'],
            ('%.3f' % task.openness) if task.openness is not None else task.openness)
        self.assertEqual(
            int(json['monitoring']['tasks'][0]['position']),
            1)
        # AND балл найденности (в первой задаче, в оценке по первому параметру)
        # в БД и json совпадает
        self.assertEqual(
            int(json['monitoring']['tasks'][0]['scores'][0]['found']),
            int(score.found))
        self.assertEqual(
            json['monitoring']['tasks'][0]['scores'][0]['type'],
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
            self.assertEqual(len(row), 18)
            if row_count == 1:
                self.assertEqual(row[0], '#Monitoring')
                continue
            else:
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
        self.client = Client()
        self.monitoring = mommy.make(
            Monitoring,
            pk=999,
            status=MONITORING_PUBLISHED)
        # AND в каждом мониторинге есть организация
        organization = mommy.make(Organization, monitoring=self.monitoring)
        # AND есть активный пользователь, не суперюзер, expert (см выше, этот - не эксперт, надо создать эксперта)
        expert1 = mommy.make_recipe('exmo2010.active_user')
        expert1.profile.is_expertB = True
        expert2 = mommy.make_recipe('exmo2010.active_user')
        expert2.profile.is_expertB = True
        # AND в каждой организации есть одобренная задача для expert
        task = mommy.make(
            Task,
            organization=organization,
            user=expert1,
            status=Task.TASK_APPROVED,
        )
        task = mommy.make(
            Task,
            organization=organization,
            user=expert2,
            status=Task.TASK_OPEN,
        )
        # AND в каждом мониторинге есть параметр parameter с одним нерелевантным критерием
        parameter = mommy.make(
            Parameter,
            monitoring=self.monitoring,
            complete=False,
            weight=1)
        # AND в каждой задаче есть оценка по parameter
        score = mommy.make(
            Score,
            task=task,
            parameter=parameter,
        )

    def test_approved_json(self):
        url = reverse('exmo2010:monitoring_export', args=[self.monitoring.pk])
        response = self.client.get(url + '?format=json')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается json
        self.assertEqual(response.get('content-type'), 'application/json')
        json = simplejson.loads(response.content)
        self.assertEqual(len(json['monitoring']['tasks']), 0, simplejson.dumps(json, indent=2))

    def test_approved_csv(self):
        url = reverse('exmo2010:monitoring_export', args=[self.monitoring.pk])
        response = self.client.get(url + '?format=csv')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается csv
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        csv = [line for line in UnicodeReader(StringIO(response.content))]
        #only header
        self.assertEqual(len(csv), 1)


class OrgUserRatingAccessTestCase(TestCase):
    # SHOULD allow org representatives to see only related orgs in unpublished ratings

    def setUp(self):

        # GIVEN MONITORING_INTERACT monitoring with 2 organizations
        self.monitoring_related = mommy.make(Monitoring, status=MONITORING_INTERACT)
        organization = mommy.make(Organization, monitoring=self.monitoring_related)
        organization_unrelated = mommy.make(Organization, monitoring=self.monitoring_related)

        # AND representative user for one organization
        user = User.objects.create_user('orguser', 'usr@svobodainfo.org', 'password')
        user.groups.add(Group.objects.get(name=user.profile.organization_group))
        user.profile.organization = [organization]

        # AND MONITORING_INTERACT monitoring with organization, not connected to representative user
        self.monitoring_unrelated = mommy.make(Monitoring, status=MONITORING_INTERACT)
        organization_unrelated2 = mommy.make(Organization, monitoring=self.monitoring_unrelated)

        # AND approved task for each organization
        self.task_related = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)
        mommy.make(Task, organization=organization_unrelated, status=Task.TASK_APPROVED)
        mommy.make(Task, organization=organization_unrelated2, status=Task.TASK_APPROVED)

        self.client = Client()
        # AND i am logged in as orguser
        self.client.login(username='orguser', password='password')

        def test_forbid_org_access_to_unrelated_unpublished_rating(self):
            url = reverse('exmo2010:monitoring_rating', args=[self.monitoring_unrelated.pk])
            # WHEN i get unrelated unpublished rating page
            response = self.client.get(url)
            # THEN response status_code is 403 (forbidden)
            self.assertEqual(response.status_code, 403)

        def test_allow_org_see_related_org_unpublished_rating(self):
            url = reverse('exmo2010:monitoring_rating', args=[self.monitoring_related.pk])
            # WHEN i get related unpublished rating page
            response = self.client.get(url)
            # THEN response status_code is 200 (OK)
            self.assertEqual(response.status_code, 200)
            tasks = [task.pk for task in response.context['rating_list']]
            # AND i see only my own task in the list
            self.assertEqual(tasks, [self.task_related.pk])


class RatingStatsTestCase(TestCase):
    # SHOULD properly calculate rating statistics

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring, openness_expression__code=8, status=MONITORING_PUBLISHED)
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

        self.client = Client()
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
