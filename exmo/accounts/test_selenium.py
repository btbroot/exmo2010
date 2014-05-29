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
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from nose.plugins.attrib import attr
from nose_parameterized import parameterized

from core.test_utils import BaseSeleniumTestCase


@attr('selenium')
class AutoDisabledCheckboxesTestCase(BaseSeleniumTestCase):
    # Scenario: Auto disabled notification checkboxes at user settings page.

    def setUp(self):
        self.url = reverse('exmo2010:settings')
        # GIVEN expertB account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.groups.add(Group.objects.get(name=expertB.profile.expertB_group))
        # AND user account without any permission
        User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND elements ids
        self.elem_type = '#id_notification_type'
        self.elem_interval = '#id_notification_interval'
        self.elem_self = '#id_notification_self'
        self.elem_thread = '#id_notification_thread'
        self.elem_subscribe = '#id_subscribe'

    @parameterized.expand([
        (0, False, 'true', 'true'),
        (1, False, None, None),
        (2, True, None, 'true'),
    ])
    def test_disable_checkboxes_for_expert(self, type_value, expected_interval_visible,
                                           expected_attr_self, expected_attr_thread):
        # WHEN expert B is logged in
        self.login('expertB', 'password')
        # AND get settings page
        self.get(self.url)
        # AND select option
        self.webdrv.find_element_by_xpath("//select[@id='id_notification_type']/option[@value='%d']" % type_value).click()
        # AND get notifications attributes
        interval_visible = self.find(self.elem_interval).is_displayed()
        attr_self = self.find(self.elem_self).get_attribute('disabled')
        attr_thread = self.find(self.elem_thread).get_attribute('disabled')
        attr_subscribe = self.find(self.elem_subscribe).get_attribute('disabled')
        # THEN notifications attributes equal expected attributes
        self.assertEqual(interval_visible, expected_interval_visible)
        self.assertEqual(attr_self, expected_attr_self)
        self.assertEqual(attr_thread, expected_attr_thread)
        self.assertEqual(attr_subscribe, None)

    def test_disable_checkboxes_for_user(self):
        # WHEN user is logged in
        self.login('user', 'password')
        # AND get settings page
        self.get(self.url)
        # AND find notifications element
        notification_type = self.find(self.elem_type)
        notification_interval = self.find(self.elem_interval)
        notification_self = self.find(self.elem_self)
        notification_thread = self.find(self.elem_thread)
        # AND get subscribe attribute
        attr_subscribe = self.find(self.elem_subscribe).get_attribute('disabled')
        # THEN elements and attribute should not be found
        self.assertEqual(notification_type, None)
        self.assertEqual(notification_interval, None)
        self.assertEqual(notification_self, None)
        self.assertEqual(notification_thread, None)
        self.assertEqual(attr_subscribe, None)
