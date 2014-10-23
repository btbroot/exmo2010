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

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase


class EmailConfirmationTestCase(TestCase):
    # exmo2010:confirm_email

    #TODO: move this testcase to *general logic* tests directory

    # Should activate user after he visits confirmation link from email.
    # Should fail if url token is forged.

    fields = 'status first_name patronymic last_name email password subscribe'.split()

    def test_after_registration(self):
        # WHEN i visit registration page (to enable test_cookie)
        self.client.get(reverse('exmo2010:registration_form'))
        # AND i submit registration form
        data = ('individual', 'first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', '')
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
        data = ('individual', 'first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', '')
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


class RegistrationEmailTestCase(TestCase):
    # exmo2010:registration_form

    #TODO: move this testcase to email tests directory

    # Should send email with activation url when registration form is submitted.

    fields = 'status first_name patronymic last_name email password subscribe'.split()

    def test_registration(self):
        # WHEN i visit registration page (to enable test_cookie)
        self.client.get(reverse('exmo2010:registration_form'))
        # AND i submit registration form
        data = ('representative', 'first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', '')
        response = self.client.post(reverse('exmo2010:registration_form'), dict(zip(self.fields, data)))
        # THEN i should be redirected to the please_confirm_email page
        self.assertRedirects(response, reverse('exmo2010:please_confirm_email'))
        # AND one email message should be sent
        self.assertEqual(len(mail.outbox), 1)


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
