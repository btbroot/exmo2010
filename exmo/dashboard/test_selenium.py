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
from datetime import date
from urlparse import urlparse

from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse_lazy
from model_mommy import mommy
from nose.plugins.attrib import attr
from nose_parameterized import parameterized

from core.test_utils import BaseSeleniumTestCase
from exmo2010.models import Monitoring, Organization, Task
from exmo2010.models.monitoring import MONITORING_PUBLISHED


ACCOUNT = {
    1: '#account-menu > li:nth-child(1) a',
    2: '#account-menu > li:nth-child(2) a',
    3: '#account-menu > li:nth-child(3) a'
}

NAVIGATION = {
    1: '#navigation-menu > li:nth-child(1) a',
    2: '#navigation-menu > li:nth-child(2) a',
    3: '#navigation-menu > li:nth-child(3) a',
    4: '#navigation-menu > li:nth-last-child(4) a',
    5: '#navigation-menu > li:nth-last-child(3) a',
    6: '#navigation-menu > li:nth-last-child(2) a'
}

MSG = {
    1: '#navigation-menu > li:nth-child(3) ul > li:nth-child(1) a',
    2: '#navigation-menu > li:nth-child(3) ul > li:nth-child(2) a',
    3: '#navigation-menu > li:nth-child(3) ul > li:nth-child(3) a'
}

URLS = {
    'index': reverse_lazy('exmo2010:index'),
    'login': reverse_lazy('exmo2010:auth_login'),
    'logout': reverse_lazy('exmo2010:auth_logout'),
    'registration': reverse_lazy('exmo2010:registration_form'),
    'settings': reverse_lazy('exmo2010:settings'),
    'admin': reverse_lazy('admin:index'),
    'comment': reverse_lazy('exmo2010:comment_list'),
    'clarification': reverse_lazy('exmo2010:clarification_list'),
    'claim': reverse_lazy('exmo2010:claim_list'),
    'ratings': reverse_lazy('exmo2010:ratings'),
    'statistics': reverse_lazy('exmo2010:monitoring_report'),
    'help': reverse_lazy('exmo2010:help'),
}


@attr('selenium')
class HeaderMenuTestCase(BaseSeleniumTestCase):
    # Scenario: Checking items in header menu

    def setUp(self):
        self.url = reverse_lazy('exmo2010:index')

        # GIVEN admin account
        admin = User.objects.create_superuser('admin', 'admin@svobodainfo.org', 'password')

        # AND expert A account
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.groups.add(Group.objects.get(name=expertA.profile.expertA_group))

        # AND expert B account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.groups.add(Group.objects.get(name=expertB.profile.expertB_group))

        # AND staff user account
        staff = User.objects.create_user('staff', 'staff@svobodainfo.org', 'password')
        staff.is_staff = True
        staff.save()

        # AND published monitoring
        self.monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED, publish_date=date.today())
        # AND organzation at this monitoring
        self.organization = mommy.make(Organization, monitoring=self.monitoring)
        # AND task for expert B
        self.task = mommy.make(
            Task,
            organization=self.organization,
            user=expertB,
            status=Task.TASK_APPROVED,
        )
        # AND organization representative account
        org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        org.groups.add(Group.objects.get(name=org.profile.organization_group))
        org.profile.organization.add(self.organization)
        org.first_name = 'Org'
        org.save()

    @parameterized.expand([
        (None, {
            ACCOUNT[1]: URLS['registration'],
            ACCOUNT[2]: URLS['login']
        }),
        ('expertA', {
            ACCOUNT[2]: URLS['settings'],
            ACCOUNT[3]: URLS['logout']
        }),
        ('org', {
            ACCOUNT[2]: URLS['settings'],
            ACCOUNT[3]: URLS['logout']
        }),
        ('admin', {
            ACCOUNT[2]: URLS['settings'],
            ACCOUNT[3]: URLS['logout'],
            NAVIGATION[3]: URLS['admin']
        }),
        ('expertB', {
            ACCOUNT[2]: URLS['settings'],
            ACCOUNT[3]: URLS['logout'],
            MSG[1]: URLS['comment'],
            MSG[2]: URLS['clarification'],
            MSG[3]: URLS['claim']
        }),
        ('staff', {
            ACCOUNT[2]: URLS['settings'],
            ACCOUNT[3]: URLS['logout'],
            NAVIGATION[3]: URLS['admin']
        }),
    ])
    def test_menu(self, user, params):
        # WHEN user is logged in
        if user:
            self.login(user, 'password')
        # AND get index page
        self.get(self.url)

        # THEN links equal expected results for any user
        self.assertEqual(self.get_url_path(NAVIGATION[1]), URLS['index'])
        self.assertEqual(self.get_url_path(NAVIGATION[2]), URLS['index'])
        self.assertEqual(self.get_url_path(NAVIGATION[4]), URLS['ratings'])
        self.assertEqual(self.get_url_path(NAVIGATION[5]), URLS['statistics'])
        self.assertEqual(self.get_url_path(NAVIGATION[6]), URLS['help'])

        for element, expected_url in params.items():
            self.assertEqual(self.get_url_path(element), expected_url)

        if user == 'org':
            self.assertEqual(self.get_url_path(NAVIGATION[3]),
                             reverse_lazy('exmo2010:recommendations', args=[self.task.id]))

    def get_url_path(self, selector):
        """
        Return url path without domain.

        """
        url_path = urlparse(self.find(selector).get_attribute('href')).path

        return url_path
