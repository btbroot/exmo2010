# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
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
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.test import TestCase
from model_mommy import mommy
from nose_parameterized import parameterized

from exmo2010.models import Monitoring, Organization, Parameter, Task, MONITORING_INTERACTION


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

        self.url = reverse('exmo2010:parameter_update', args=[task.pk, self.parameter.pk])

    def test_anonymous_param_edit_get(self):
        # WHEN anonymous user gets parameter edit page
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
    def test_param_edit_get(self, username, expected_response_code):
        self.client.login(username=username, password='password')

        # WHEN user gets parameter edit page
        response = self.client.get(self.url)

        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand([
        ('user',),
        ('org',),
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
        # GIVEN monitoring with parameter and task
        self.monitoring = mommy.make(Monitoring)
        self.param1 = mommy.make(Parameter, code=123, name='asd', monitoring=self.monitoring)
        self.task = mommy.make(Task, organization__monitoring=self.monitoring)

        # AND i am logged in as expertA:
        self.expertA = User.objects.create_user('expertA', 'A@ya.ru', 'password')
        self.expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

    def test_duplicate_code(self):
        formdata = dict(code=self.param1.code, name_en='123', monitoring=99, weight=1)
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
        formdata = dict(code='456', name_en=self.param1.name, monitoring=99, weight=1)
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
        formdata = dict(code='456', name_en='ppp', monitoring=99, weight=1)
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
        # GIVEN expertA and expertB:
        self.expertA = User.objects.create_user('expertA', 'A@ya.ru', 'password')
        self.expertA.profile.is_expertA = True
        self.expertB = User.objects.create_user('expertB', 'B@ya.ru', 'password')
        self.expertB.profile.is_expertB = True

        # AND i am logged in as expertA:
        self.client.login(username='expertA', password='password')

        # AND Monitoring with Organization and Parameter
        monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        organization = mommy.make(Organization, monitoring=monitoring)
        self.parameter = mommy.make(Parameter, monitoring=monitoring)

        # AND Task assigned to expertB
        self.task = mommy.make(Task, organization=organization, user=self.expertB)

        # NOTE: pop message about task assignment to expertB
        # TODO: get rid of this automatic email on Task creation, move to the view
        mail.outbox.pop()

    def test_email_notify(self):
        url = reverse('exmo2010:parameter_update', args=[self.task.pk, self.parameter.pk])

        # WHEN i submit parameter form with "save and notify" button
        formdata = dict(model_to_dict(self.parameter), monitoring=self.parameter.monitoring_id, submit_and_send=True)
        response = self.client.post(url, follow=True, data=formdata)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND there should be 2 email messages in the outbox
        self.assertEqual(len(mail.outbox), 2)

        # AND both expertA and expertB should get the email
        self.assertEqual(set(tuple(m.to) for m in mail.outbox), set([('A@ya.ru',), ('B@ya.ru',)]))
