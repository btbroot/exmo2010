# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
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
import os

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy import mommy
from nose_parameterized import parameterized

from exmo2010.custom_registration.forms import RegistrationFormFull, RegistrationFormShort
from exmo2010.models import Monitoring, Organization, MONITORING_INTERACTION


class RegistrationFormTestCase(TestCase):
    # Registration forms should properly validate input data

    user_fields = 'status first_name patronymic last_name email password subscribe'.split()
    orguser_fields = user_fields + 'position phone invitation_code'.split()

    def setUp(self):
        # GIVEN: interaction monitoring
        monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        # AND organization
        self.organization = mommy.make(Organization, monitoring=monitoring)

    @parameterized.expand([
        ('0', 'first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', ''),
        ('1', 'first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', ''),
    ])
    def test_valid_user_registration_form(self, *values):
        # WHEN form initialized with valid data
        form = RegistrationFormShort(data=dict(zip(self.user_fields, values)))
        # THEN form validation should succeed
        self.assertEqual(form.is_valid(), True)

    @parameterized.expand([
        ('', 'first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', ''),
    ])
    def test_invalid_user_registration_form(self, *values):
        # WHEN form initialized with invalid data
        form = RegistrationFormShort(data=dict(zip(self.user_fields, values)))
        # THEN form validation should fail
        self.assertEqual(form.is_valid(), False)

    @parameterized.expand([
        ('0', 'first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', '', '', ''),
        ('1', 'first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', '', '', ''),
    ])
    def test_valid_orguser_registration_form(self, *values):
        values = values + (self.organization.inv_code,)
        # WHEN form initialized with valid data
        form = RegistrationFormFull(data=dict(zip(self.orguser_fields, values)))
        # THEN form validation should succeed
        self.assertEqual(form.is_valid(), True)

    @parameterized.expand([
        ('', 'first_name', 'patronymic', 'last_name', 'test@mail.com', 'password', '', '', ''),
    ])
    def test_invalid_orguser_registration_form(self, *values):
        values = values + (self.organization.inv_code,)
        # WHEN form initialized with invalid data
        form = RegistrationFormFull(data=dict(zip(self.orguser_fields, values)))
        # THEN form validation should fail
        self.assertEqual(form.is_valid(), False)


class ActivationTestCase(TestCase):
    # SHOULD allow activation with correct activation key only

    def test_activation_with_invalid_key(self):
        # WHEN anonymous user tries to activate account with the right length random key
        activation_key = os.urandom(20).encode('hex')
        url = reverse('exmo2010:registration_activate', args=[activation_key])
        response = self.client.get(url, follow=True)
        # THEN anonymous should be redirected to the login page
        self.assertRedirects(response, unicode(settings.LOGIN_URL))