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
#    along with this program.  If not, see <http://www.gnu.usr/licenses/>.
#
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from nose_parameterized import parameterized

from accounts.forms import SubscribeForm, SubscribeAndNotifyForm
from exmo2010.models import *


class FormsTestCase(TestCase):
    # Scenario: Form tests
    @parameterized.expand([
        (False,),
        (True,),
    ])
    def test_subscribe_form(self, subscribe):
        # WHEN user send SubscribeForm with data
        form_data = {'subscribe': subscribe}
        form = SubscribeForm(data=form_data)
        # THEN form is valid
        self.assertEqual(form.is_valid(), True)

    @parameterized.expand([
        (False, 0, 1, False, False),
        (False, 1, 3, True, False),
        (False, 2, 6, False, True),
        (True, 0, 12, True, True),
        (True, 1, 24, False, False),
        (True, 2, 12, True, False),
    ])
    def test_subscribe_and_notify_form(self, subscribe, notification_type, notification_interval,
                                       notification_self, notification_thread):
        # WHEN user send SubscribeAndNotifyForm with data
        form_data = {
            'subscribe': subscribe,
            'notification_type': notification_type,
            'notification_interval': notification_interval,
            'notification_self': notification_self,
            'notification_thread': notification_thread,
        }
        form = SubscribeAndNotifyForm(data=form_data)
        # THEN form is valid
        self.assertEqual(form.is_valid(), True)


class SettingsViewTestCase(TestCase):
    # Scenario: Settings view tests
    def setUp(self):
        # GIVEN registered user without any permissions
        self.user = User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND expert B
        self.expertb = User.objects.create_user('expertb', 'expertb@svobodainfo.org', 'password')
        self.expertb.groups.add(Group.objects.get(name=self.expertb.profile.expertB_group))
        self.url = reverse('exmo2010:settings')
        self.client = Client()

    def test_user_settings(self):
        # WHEN user login
        self.client.login(username='user', password='password')
        # AND submit notification form
        data = {
            'notify_submit': 'some_value',
            'subscribe': True,
        }
        response = self.client.post(self.url, data)
        # THEN response code is 200
        self.assertEqual(response.status_code, 200)
        user_profile = UserProfile.objects.get(user=self.user)
        # AND user profile settings was changed
        self.assertEqual(user_profile.subscribe, True)

    @parameterized.expand([
        (False, 0, 1, False),
        (False, 1, 3, True),
        (False, 2, 6, False),
        (True, 0, 12, True),
        (True, 1, 24, False),
        (True, 2, 12, True),
    ])
    def test_expertb_settings(self, subscribe, notification_type, notification_interval, notification_self):
        # WHEN expert B login
        self.client.login(username='expertb', password='password')
        # AND submit notification form
        data = {
            'notify_submit': 'some_value',
            'subscribe': subscribe,
            'notification_type': notification_type,
            'notification_interval': notification_interval,
            'notification_self': notification_self,
        }
        response = self.client.post(self.url, data)
        # THEN response code is 200
        self.assertEqual(response.status_code, 200)
        expertb_profile = UserProfile.objects.get(user=self.expertb)
        # AND expert B profile settings was changed
        self.assertEqual(expertb_profile.subscribe, subscribe)
        self.assertEqual(expertb_profile.notification_type, notification_type)
        self.assertEqual(expertb_profile.notification_interval, notification_interval)
        self.assertEqual(expertb_profile.notification_self, notification_self)
