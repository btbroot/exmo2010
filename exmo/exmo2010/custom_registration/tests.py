# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
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
import re
from urllib import urlencode

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy import mommy

from exmo2010.models import Monitoring, Organization, Task, MONITORING_INTERACTION


class EmailConfirmationTestCase(TestCase):
    # exmo2010:confirm_email

    #TODO: move this testcase to *general logic* tests directory

    # Should activate user after he visits confirmation link from email.
    # Should fail if url token is forged.

    fields = 'first_name patronymic last_name email password subscribe'.split()

    def test_after_registration(self):
        # WHEN i visit registration page (to enable test_cookie)
        self.client.get(reverse('exmo2010:registration_form'))
        # AND i submit registration form
        data = ('first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', '')
        response = self.client.post(reverse('exmo2010:registration_form'), dict(zip(self.fields, data)))

        # THEN i should be redirected to the please_confirm_email page
        self.assertRedirects(response, reverse('exmo2010:please_confirm_email'))
        # AND one user should be created with email_confirmed=False and is_active=False
        all_confirmed = [u.profile.email_confirmed for u in User.objects.all()]
        all_active = [u.is_active for u in User.objects.all()]
        self.assertEqual(all_confirmed, [False])
        self.assertEqual(all_active, [False])
        # AND one email message should be sent
        self.assertEqual(len(mail.outbox), 1)

        # WHEN i visit confirmation link
        url = re.search('http://(?P<host>[^/]+)(?P<rel_url>[^\s]+)', mail.outbox[0].body).group('rel_url')
        response = self.client.get(url)

        # THEN i should be redirected to the index page
        self.assertRedirects(response, reverse('exmo2010:index'))
        # AND user should be activated with email_confirmed=True and is_active=True
        all_confirmed = [u.profile.email_confirmed for u in User.objects.all()]
        all_active = [u.is_active for u in User.objects.all()]
        self.assertEqual(all_confirmed, [True])
        self.assertEqual(all_active, [True])

    def test_after_resend_email(self):
        # GIVEN existing non-activated user
        user = User.objects.create_user('org', 'test@mail.com', 'password')
        user.is_active = False
        user.save()
        user.profile.email_confirmed = False
        user.profile.save()

        # WHEN i submit resend confirmation email form
        response = self.client.post(reverse('exmo2010:auth_resend_email'), {'email': 'test@mail.com'})

        # THEN i should be redirected to the please_confirm_email page
        self.assertRedirects(response, reverse('exmo2010:please_confirm_email'))
        # AND one user should be created with email_confirmed=False and is_active=False
        all_confirmed = [u.profile.email_confirmed for u in User.objects.all()]
        all_active = [u.is_active for u in User.objects.all()]
        self.assertEqual(all_confirmed, [False])
        self.assertEqual(all_active, [False])
        # AND one email message should be sent
        self.assertEqual(len(mail.outbox), 1)

        # WHEN i visit confirmation link
        url = re.search('http://(?P<host>[^/]+)(?P<rel_url>[^\s]+)', mail.outbox[0].body).group('rel_url')
        response = self.client.get(url)

        # THEN i should be redirected to the index page
        self.assertRedirects(response, reverse('exmo2010:index'))
        # AND user should be activated with email_confirmed=True and is_active=True
        all_confirmed = [u.profile.email_confirmed for u in User.objects.all()]
        all_active = [u.is_active for u in User.objects.all()]
        self.assertEqual(all_confirmed, [True])
        self.assertEqual(all_active, [True])

    def test_forged_confirmation_url(self):
        # WHEN i visit registration page (to enable test_cookie)
        self.client.get(reverse('exmo2010:registration_form'))
        # AND i submit registration form
        data = ('first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', '')
        response = self.client.post(reverse('exmo2010:registration_form'), dict(zip(self.fields, data)))

        # WHEN i visit forged confirm_email url
        url = reverse('exmo2010:confirm_email', args=[User.objects.all()[0].pk, '122-2342262654'])
        response = self.client.get(url, follow=True)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND user should still have email_confirmed=False and is_active=False
        all_confirmed = [u.profile.email_confirmed for u in User.objects.all()]
        all_active = [u.is_active for u in User.objects.all()]
        self.assertEqual(all_confirmed, [False])
        self.assertEqual(all_active, [False])


class RegistrationWithKnownOrgEmailTestCase(TestCase):
    # exmo2010:registration_form

    #TODO: move this testcase to general logic tests directory

    # If registering user email matches any organization email which he is willing to represent, he should be activated
    # immediately after registration form is submitted.
    # If task for given org exists and user has permission to view it - redirect him to the task recommendations page.
    # Otherwise redirect him to the front page

    def setUp(self):
        # GIVEN organization in INTERACTION monitoring
        self.org = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION, email='org@test.ru')

    def test_registration_with_task_accessible(self):
        # GIVEN approved task for existing org
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        task = mommy.make(Task, organization=self.org, status=Task.TASK_APPROVED, user=expertB)
        # NOTE: pop email message about task assignment
        mail.outbox.pop()

        # WHEN i visit registration page (to enable test_cookie)
        self.client.get(reverse('exmo2010:registration_form'))
        # AND i submit registration form
        url = reverse('exmo2010:registration_form') + '?code={}'.format(self.org.inv_code)
        response = self.client.post(url, {'email': self.org.email, 'password': 'password'})

        # THEN i should be redirected to the front page
        self.assertRedirects(response, reverse('exmo2010:recommendations', args=(task.pk,)))
        # AND no email message should be sent
        self.assertEqual(len(mail.outbox), 0)
        # AND 2 users should exist in database (new user and task expertB)
        emails = set(User.objects.values_list('email', flat=True))
        self.assertEqual(emails, {'expertB@svobodainfo.org', self.org.email})
        # AND user should be activated with email_confirmed=True and is_active=True
        all_confirmed = [u.profile.email_confirmed for u in User.objects.all()]
        all_active = [u.is_active for u in User.objects.all()]
        self.assertEqual(all_confirmed, [True, True])
        self.assertEqual(all_active, [True, True])

    def test_registration_without_task(self):
        # WHEN i visit registration page (to enable test_cookie)
        self.client.get(reverse('exmo2010:registration_form'))
        # AND i submit registration form
        url = reverse('exmo2010:registration_form') + '?code={}'.format(self.org.inv_code)
        response = self.client.post(url, {'email': self.org.email, 'password': 'password'})

        # THEN i should be redirected to the front page
        self.assertRedirects(response, reverse('exmo2010:index'))
        # AND no email message should be sent
        self.assertEqual(len(mail.outbox), 0)
        # AND user should be activated with email_confirmed=True and is_active=True
        all_confirmed = [u.profile.email_confirmed for u in User.objects.all()]
        all_active = [u.is_active for u in User.objects.all()]
        self.assertEqual(all_confirmed, [True])
        self.assertEqual(all_active, [True])


class RegistrationEmailTestCase(TestCase):
    # exmo2010:registration_form

    #TODO: move this testcase to email tests directory

    # If registering user email does not match any organization email which he is willing to represent,
    # email message with activation url should be sent when registration form is submitted.

    def test_registration(self):
        # WHEN i visit registration page (to enable test_cookie)
        self.client.get(reverse('exmo2010:registration_form'))
        # AND i submit registration form
        form_data = {'status': 'representative', 'email': 'test@mail.com', 'password': '123'}
        response = self.client.post(reverse('exmo2010:registration_form'), form_data)

        # THEN i should be redirected to the please_confirm_email page
        self.assertRedirects(response, reverse('exmo2010:please_confirm_email'))
        # AND one email message should be sent
        self.assertEqual(len(mail.outbox), 1)


class RegistrationWithInvCodesAndRedirectTestCase(TestCase):
    # exmo2010:registration_form

    # If registering user email matches any organization email which he is willing to represent,
    # he should be redirected to the recommendations page if the count of organizations equals one,
    # or to the index page if the count of organizations more then one.
    # Otherwise redirect him to the please_confirm_email page.

    def setUp(self):
        # GIVEN INTERACTION monitoring
        self.monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        # AND two organizations with unique emails
        self.org1 = mommy.make(Organization, monitoring=self.monitoring, email='org1@test.ru')
        self.org2 = mommy.make(Organization, monitoring=self.monitoring, email='org2@test.ru')
        # AND approved task for each organization
        self.task1 = mommy.make(Task, organization=self.org1, status=Task.TASK_APPROVED)
        self.task2 = mommy.make(Task, organization=self.org2, status=Task.TASK_APPROVED)
        # AND url for GET and POST requests
        self.url = reverse('exmo2010:registration_form')

    def test_two_codes_and_not_orgs_email(self):
        user_email = 'usr@svobodainfo.org'
        # WHEN I get registration page with 2 invitation codes and not orgs email in GET params
        params = {'code': [self.org1.inv_code, self.org2.inv_code], 'email': user_email}
        url = self.url + '?' + urlencode(params, True)
        response_get = self.client.get(url)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response_get.status_code, 200)

        # WHEN I get all initial values and add value for password field
        data = response_get.context['form'].initial
        data.update({'password': 'password'})
        # AND submit form
        response_post = self.client.post(url, data)
        # THEN I should be redirected to the please_confirm_email page
        self.assertRedirects(response_post, reverse('exmo2010:please_confirm_email'))
        # AND I shouldn't be connected to any organizations from url
        user = User.objects.get(email=user_email)
        self.assertEqual(set(user.profile.organization.values_list('inv_code', flat=True)), set([]))

    def test_two_codes_and_org_email(self):
        # WHEN I get registration page with 2 invitation codes and org email in GET params
        params = {'code': [self.org1.inv_code, self.org2.inv_code], 'email': self.org1.email}
        url = self.url + '?' + urlencode(params, True)
        response_get = self.client.get(url)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response_get.status_code, 200)

        # WHEN I get all initial values and add value for password field
        data = response_get.context['form'].initial
        data.update({'password': 'password'})
        # AND submit form
        response_post = self.client.post(url, data)
        # THEN I should be redirected to the index page
        self.assertRedirects(response_post, reverse('exmo2010:index'))
        # AND I should be connected to 2 organizations from url
        user = User.objects.get(email=self.org1.email)
        self.assertEqual(set(user.profile.organization.values_list('inv_code', flat=True)),
                         {self.org1.inv_code, self.org2.inv_code})

    def test_one_code_and_org_email(self):
        # WHEN I get registration page with 1 invitation code and org email in GET params
        params = {'code': [self.org1.inv_code], 'email': self.org1.email}
        url = self.url + '?' + urlencode(params, True)
        response_get = self.client.get(url)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response_get.status_code, 200)

        # WHEN I get all initial values and add value for password field
        data = response_get.context['form'].initial
        data.update({'password': 'password'})
        # AND submit form
        response_post = self.client.post(url, data)
        # THEN I should be redirected to the recommendations page
        self.assertRedirects(response_post, reverse('exmo2010:recommendations', args=(self.task1.pk,)))
        # AND I should be connected to 1 organization from url
        user = User.objects.get(email=self.org1.email)
        self.assertEqual(set(user.profile.organization.values_list('inv_code', flat=True)), {self.org1.inv_code})


class ResendConfirmationEmailTestCase(TestCase):
    # exmo2010:auth_resend_email

    #TODO: move this testcase to email tests directory

    # Should send email when resend activation email form submitted.

    def setUp(self):
        # GIVEN existing user
        User.objects.create_user('user', 'test@mail.com', 'password')

    def test_resend(self):
        # WHEN i submit resend email form
        response = self.client.post(reverse('exmo2010:auth_resend_email'), {'email': 'test@mail.com'})
        # THEN i should be redirected to the please_confirm_email page
        self.assertRedirects(response, reverse('exmo2010:please_confirm_email'))
        # AND one email message should be sent
        self.assertEqual(len(mail.outbox), 1)


class PasswordResetEmailTestCase(TestCase):
    # exmo2010:password_reset_request

    #TODO: move this testcase to email tests directory

    # Should send email with password reset url when reset password form is submitted.

    def setUp(self):
        # GIVEN existing user
        User.objects.create_user('user', 'test@mail.com', 'password')

    def test_password_reset(self):
        # WHEN i submit reset password form
        response = self.client.post(reverse('exmo2010:password_reset_request'), {'email': 'test@mail.com'})
        # THEN i should be redirected to the password_reset_sent page
        self.assertRedirects(response, reverse('exmo2010:password_reset_sent'))
        # AND one email message should be sent
        self.assertEqual(len(mail.outbox), 1)


class PasswordResetConfirmTestCase(TestCase):
    # exmo2010:password_reset_confirm

    #TODO: move this testcase to general logic tests directory

    # Valid reset url should show password reset form, which should allow to update password.

    def setUp(self):
        # GIVEN existing user
        self.user = User.objects.create_user('user', 'test@mail.com', 'password')

    def test_password_reset(self):
        # WHEN i submit reset password form
        response = self.client.post(reverse('exmo2010:password_reset_request'), {'email': 'test@mail.com'})
        # THEN i should be redirected to the password_reset_sent page
        self.assertRedirects(response, reverse('exmo2010:password_reset_sent'))
        # AND one email message should be sent
        self.assertEqual(len(mail.outbox), 1)

        # WHEN i visit confirmation link
        url = re.search('http://(?P<host>[^/]+)(?P<rel_url>[^\s]+)', mail.outbox[0].body).group('rel_url')
        response = self.client.get(url)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND new_password form should be displayed.
        self.assertTrue('new_password_form' in response.content)

        # WHEN i submit new_password form with new password
        response = self.client.post(url, {'new_password': 'new'})

        # THEN i should be redirected to the index page
        self.assertRedirects(response, reverse('exmo2010:index'))
        # AND user password should change
        user = authenticate(username='user', password='new')
        self.assertEqual(self.user, user)
