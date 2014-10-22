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
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.test import TestCase
from mock import MagicMock, Mock
from model_mommy import mommy
from nose_parameterized import parameterized

from .views import PostOrgParamRelevanceView
from core.test_utils import OptimizedTestCase
from exmo2010.models import Monitoring, ObserversGroup, Organization, Parameter, Score, Task


class ParameterEditAccessTestCase(TestCase):
    # SHOULD allow only expertA to edit parameter

    def setUp(self):
        # GIVEN monitoring with organization, task and parameter
        self.monitoring = mommy.make(Monitoring)
        organization = mommy.make(Organization, monitoring=self.monitoring)
        task = mommy.make(Task, organization=organization)
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1, code=1, name='initial')

        # AND user without any permissions
        User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND superuser
        User.objects.create_superuser('admin', 'admin@svobodainfo.org', 'password')
        # AND expert B
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND expert A
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND organization representative
        org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        org.profile.organization = [organization]
        # AND observer user
        observer = User.objects.create_user('observer', 'observer@svobodainfo.org', 'password')
        # AND observers group for monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=self.monitoring)
        obs_group.organizations = [organization]
        obs_group.users = [observer]

        self.url = reverse('exmo2010:parameter_update', args=[task.pk, self.parameter.pk])

    def test_anonymous_param_edit_get(self):
        # WHEN anonymous user gets parameter edit page
        response = self.client.get(self.url, follow=True)
        # THEN he is redirected to login page
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + self.url)

    @parameterized.expand([
        ('user', 403),
        ('org', 403),
        ('observer', 403),
        ('expertB', 403),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_param_edit_get(self, username, expected_response_code):
        self.client.login(username=username, password='password')

        # WHEN user gets parameter edit page
        response = self.client.get(self.url)

        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand([
        ('user',),
        ('org',),
        ('observer',),
        ('expertB',),
    ])
    def test_forbid_unauthorized_param_edit_post(self, username):
        self.client.login(username=username, password='password')

        # WHEN unauthorized user forges and POSTs parameter edit form with changed weight, code and name
        self.client.post(self.url, dict(monitoring=self.monitoring.pk, code=2, weight=2, name='forged'))

        # THEN parameter does not get changed in the database
        initial_fields = {f: getattr(self.parameter, f) for f in 'weight code name'.split()}
        new_param_fields = Parameter.objects.values(*initial_fields).get(pk=self.parameter.pk)
        self.assertEqual(new_param_fields, initial_fields)


class DuplicateParamCreationTestCase(TestCase):
    # SHOULD return validation error if parameter with already existing code or name is added

    def setUp(self):
        # GIVEN  parameter and task in monitoring
        self.param1 = mommy.make(Parameter, code=123, name='asd')
        self.task = mommy.make(Task, organization__monitoring=self.param1.monitoring)

        # AND i am logged in as expertA:
        self.expertA = User.objects.create_user('expertA', 'A@ya.ru', 'password')
        self.expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

    def test_duplicate_code(self):
        formdata = dict(code=self.param1.code, name_en='123', weight=1)
        # WHEN I submit parameter add form with existing parameter code
        response = self.client.post(reverse('exmo2010:parameter_add', args=[self.task.pk]), formdata)
        # THEN no new parameters shoud get created in database
        self.assertEqual(list(Parameter.objects.all()), [self.param1])
        # AND response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND error message should say that such code exists
        errors = {'__all__': [u'Parameter with this Code and Monitoring already exists.']}
        self.assertEqual(response.context['form'].errors, errors)

    def test_duplicate_name(self):
        formdata = dict(code='456', name_en=self.param1.name, weight=1)
        # WHEN I submit parameter add form with existing parameter code
        response = self.client.post(reverse('exmo2010:parameter_add', args=[self.task.pk]), formdata)
        # THEN no new parameters shoud get created in database
        self.assertEqual(list(Parameter.objects.all()), [self.param1])
        # AND response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND error message should say that such code exists
        errors = {'__all__': [u'Parameter with this Name [en] and Monitoring already exists.']}
        self.assertEqual(response.context['form'].errors, errors)


class ParamCreateTestCase(TestCase):
    # test adding parameter using form

    def setUp(self):
        # GIVEN monitoring with task
        self.monitoring = mommy.make(Monitoring)
        self.task = mommy.make(Task, organization__monitoring=self.monitoring)

        # AND i am logged in as expertA:
        self.expertA = User.objects.create_user('expertA', 'A@ya.ru', 'password')
        self.expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

    def test_add_param(self):
        formdata = dict(code='456', name_en='ppp', weight=1)
        # WHEN I submit parameter add form
        response = self.client.post(reverse('exmo2010:parameter_add', args=[self.task.pk]), formdata)
        # THEN new parameter shoud get created in database
        params = Parameter.objects.values_list(*'code name weight monitoring_id'.split())
        self.assertEqual(list(params), [(456, 'ppp', 1, self.monitoring.pk)])
        # AND response should redirect to task_scores
        self.assertRedirects(response, reverse('exmo2010:task_scores', args=[self.task.pk]))


class ParamEditEmailNotifyTestCase(TestCase):
    # SHOULD send notification email to related experts if expertA clicked "save and notify" on parameter edit page

    def setUp(self):
        # GIVEN i am logged in as expertA:
        self.expertA = User.objects.create_user('expertA', 'A@ya.ru', 'password')
        self.expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

        # AND organization, parameter and task in monitoring
        org = mommy.make(Organization)
        self.parameter = mommy.make(Parameter, monitoring=org.monitoring)
        self.task = mommy.make(Task, organization=org, user__email='B@ya.ru')

        # NOTE: pop message about task assignment to expertB
        # TODO: get rid of this automatic email on Task creation, move to the view
        mail.outbox.pop()

    def test_email_notify(self):
        url = reverse('exmo2010:parameter_update', args=[self.task.pk, self.parameter.pk])

        # WHEN i submit parameter form with "save and notify" button
        formdata = dict(model_to_dict(self.parameter), submit_and_send=True)
        response = self.client.post(url, follow=True, data=formdata)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND there should be 2 email messages in the outbox
        self.assertEqual(len(mail.outbox), 2)

        # AND both expertA and expertB should get the email
        self.assertEqual(set(tuple(m.to) for m in mail.outbox), set([('A@ya.ru',), ('B@ya.ru',)]))


class ParamEditValidTestCase(TestCase):
    # Should modify parameter in database on valid parameter edit form submission.

    def setUp(self):
        # GIVEN i am logged in as expertA:
        self.expertA = User.objects.create_user('expertA', 'A@ya.ru', 'password')
        self.expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

        # AND organization, parameter and task in monitoring
        org = mommy.make(Organization)
        self.parameter = mommy.make(Parameter, monitoring=org.monitoring, name_en='param', notes_en='123')
        self.task = mommy.make(Task, organization=org, user__email='B@ya.ru')
        self.url = reverse('exmo2010:parameter_update', args=[self.task.pk, self.parameter.pk])

    def test_edit_name(self):
        # WHEN i submit parameter form with new name_en
        formdata = dict(model_to_dict(self.parameter), name_en='changed')
        response = self.client.post(self.url, follow=True, data=formdata)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND name_en should change in database
        self.assertEqual(list(Parameter.objects.values('name_en')), [{'name_en': 'changed'}])

    def test_clear_notes_en(self):
        ''' BUG 2031: Should clear notes_en field in database when empty notes_en submitted with edit form. '''

        # WHEN i submit parameter form with "notes_en" set to empty string
        formdata = dict(model_to_dict(self.parameter), notes_en='')
        response = self.client.post(self.url, follow=True, data=formdata)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND notes_en should change to NULL (None) in database
        self.assertEqual(list(Parameter.objects.values('notes_en')), [{'notes_en': None}])


class PostOrgParamRelevanceAccessTestCase(OptimizedTestCase):
    # exmo2010:post_org_param_relevance

    # Should always redirect anonymous to login page.
    # Should forbid all get requests.
    # Should allow post admin and expert A only.

    @classmethod
    def setUpClass(cls):
        super(PostOrgParamRelevanceAccessTestCase, cls).setUpClass()

        cls.users = {}
        # GIVEN monitoring with organization, task and parameter
        cls.monitoring = mommy.make(Monitoring)
        organization = mommy.make(Organization, monitoring=cls.monitoring)
        cls.task = mommy.make(Task, organization__monitoring=cls.monitoring)
        cls.param = mommy.make(Parameter, monitoring=cls.monitoring)
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
        cls.url = reverse('exmo2010:post_org_param_relevance')

    @parameterized.expand(zip(['GET', 'POST']))
    def test_redirect_anonymous(self, method, *args):
        # WHEN anonymous user send request to get or change parameter relevance
        request = MagicMock(user=self.users['anonymous'], method=method)
        request.get_full_path.return_value = self.url
        response = PostOrgParamRelevanceView.as_view()(request)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to login page
        self.assertEqual(response['Location'], '{}?next={}'.format(settings.LOGIN_URL, self.url))

    @parameterized.expand(zip(['admin', 'expertA', 'expertB', 'orguser', 'translator', 'observer', 'user']))
    def test_forbid_get(self, username, *args):
        # WHEN authenticated user get parameter relevance
        request = Mock(user=self.users[username], method='GET')
        response = PostOrgParamRelevanceView.as_view()(request)
        # THEN response status_code should be 405 (method not allowed)
        self.assertEqual(response.status_code, 405)

    @parameterized.expand(zip(['admin', 'expertA']))
    def test_allow_post(self, username, *args):
        # WHEN admin or expert A post change parameter relevance
        request = MagicMock(user=self.users[username], method='POST',
                            POST={'param_pk': self.param.pk, 'task_pk': self.task.pk, 'set_relevant': 1})
        response = PostOrgParamRelevanceView.as_view()(request)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)

    @parameterized.expand(zip(['expertB', 'orguser', 'translator', 'observer', 'user']))
    def test_forbid_post(self, username, *args):
        # WHEN authenticated user post change parameter relevance
        request = Mock(user=self.users[username], method='POST',
                       POST={'param_pk': self.param.pk, 'task_pk': self.task.pk, 'set_relevant': 1})
        # THEN response should raise PermissionDenied exception
        self.assertRaises(PermissionDenied, PostOrgParamRelevanceView.as_view(), request)


class PostOrgParamRelevanceTestCase(OptimizedTestCase):
    # exmo2010:post_org_param_relevance

    # Should set parameter relevance and redirect to score page if score is already exist.
    # Otherwise redirect to 'score add' page.

    @classmethod
    def setUpClass(cls):
        super(PostOrgParamRelevanceTestCase, cls).setUpClass()

        # GIVEN monitoring with task and organization
        cls.monitoring = mommy.make(Monitoring)
        cls.org = mommy.make(Organization, monitoring=cls.monitoring)
        cls.task = mommy.make(Task, organization=cls.org)
        # AND nonrelevant parameter with score
        cls.param = mommy.make(Parameter, monitoring=cls.monitoring)
        cls.param.exclude.add(cls.org)
        cls.score = mommy.make(Score, task=cls.task, parameter=cls.param)
        # AND nonrelevant parameter without score
        cls.param_without_score = mommy.make(Parameter, monitoring=cls.monitoring)
        cls.param_without_score.exclude.add(cls.org)
        # AND expert A
        cls.expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        cls.expertA.profile.is_expertA = True

    def test_score_add_redirect(self):
        # WHEN expert A change parameter relevance for parameter without score
        request = MagicMock(user=self.expertA, method='POST',
                            POST={'param_pk': self.param_without_score.pk, 'task_pk': self.task.pk, 'set_relevant': 1})
        response = PostOrgParamRelevanceView.as_view()(request)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to 'score add' page
        self.assertEqual(response['Location'],
                         reverse('exmo2010:score_add', args=[self.task.pk, self.param_without_score.pk]))
        # AND parameter with score should become relevant
        self.assertEqual(Parameter.objects.get(pk=self.param_without_score.pk).exclude.count(), 0)

    def test_score_exist_redirect(self):
        # WHEN expert A change parameter relevance for parameter with score
        request = MagicMock(user=self.expertA, method='POST',
                            POST={'param_pk': self.param.pk, 'task_pk': self.task.pk, 'set_relevant': 1})
        response = PostOrgParamRelevanceView.as_view()(request)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to 'score' page
        self.assertEqual(response['Location'],
                         reverse('exmo2010:score', args=[self.score.pk]))
        # AND parameter with score should become relevant
        self.assertEqual(Parameter.objects.get(pk=self.param.pk).exclude.count(), 0)
