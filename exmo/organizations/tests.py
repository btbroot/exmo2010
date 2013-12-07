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
import re
from email.header import decode_header

from django.contrib.auth.models import User, Group
from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from livesettings import config_value
from model_mommy import mommy
from nose_parameterized import parameterized

from core.mail_tests import LocmemBackendTests
from exmo2010.models import *


class OrganizationEditAccessTestCase(TestCase):
    # SHOULD allow only expertA to edit organization

    def setUp(self):
        self.client = Client()
        # GIVEN monitoring with organization
        self.monitoring = mommy.make(Monitoring)
        self.organization = mommy.make(
            Organization, monitoring=self.monitoring, url='1.ru', email='1@ya.ru', name='initial')

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
        org.profile.organization = [self.organization]

        self.url = reverse('exmo2010:organization_manager', args=[self.monitoring.pk, self.organization.pk, 'update'])

    def test_anonymous_org_edit_get(self):
        # WHEN anonymous user gets organization edit page
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
    def test_organization_edit_get(self, username, expected_response_code):
        self.client.login(username=username, password='password')

        # WHEN user gets organization edit page
        response = self.client.get(self.url)

        # THEN response status_code equals expected
        self.assertEqual(response.status_code, expected_response_code)

    @parameterized.expand([
        ('user',),
        ('org',),
        ('expertB',),
    ])
    def test_forbid_unauthorized_organization_edit_post(self, username):
        self.client.login(username=username, password='password')

        # WHEN unauthorized user forges and POSTs organization edit form with changed url, email and name
        self.client.post(self.url, {
            'org-monitoring': self.monitoring.pk,
            'org-url': '2.ru',
            'org-email': '2@ya.ru',
            'org-name': 'forged'})

        # THEN organization does not get changed in the database
        initial_fields = {f: getattr(self.organization, f) for f in 'url email name'.split()}
        new_org_fields = Organization.objects.values(*initial_fields).get(pk=self.organization.pk)
        self.assertEqual(new_org_fields, initial_fields)


class TestOrganizationsPage(TestCase):
    # Scenario: try to get organizations page by any users
    def setUp(self):
        self.client = Client()
        # GIVEN published monitoring
        self.monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        # AND organization for this monitoring
        self.organization = mommy.make(Organization, monitoring=self.monitoring)
        # AND user without any permissions
        self.user = User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND superuser
        self.admin = User.objects.create_superuser('admin', 'admin@svobodainfo.org', 'password')
        # AND expert B
        self.expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        self.expertB.groups.add(Group.objects.get(name=self.expertB.profile.expertB_group))
        # AND expert A
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.groups.add(Group.objects.get(name=self.expertA.profile.expertA_group))
        # AND organizations representative
        self.org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        profile = self.org.get_profile()
        profile.organization = [self.organization]

    def test_anonymous_organizations_page_access(self):
        url = reverse('exmo2010:organization_list', args=[self.monitoring.pk])
        # WHEN anonymous user get organizations page
        resp = self.client.get(url)
        # THEN redirect to login page
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, settings.LOGIN_URL + '?next=' + url)

    @parameterized.expand([
        ('user', 403),
        ('org', 403),
        ('expertB', 403),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_authenticated__user_organizations_page_access(self, username, response_code):
        url = reverse('exmo2010:organization_list', args=[self.monitoring.pk])
        # WHEN user get organizations page
        self.client.login(username=username, password='password')
        resp = self.client.get(url)
        # THEN only admin and expert A have access
        self.assertEqual(resp.status_code, response_code)


class SendOrgsEmailTestCase(LocmemBackendTests, TestCase):
    # Scenario: send and check emails
    def setUp(self):
        self.client = Client()
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND ten organizations connected to monitoring
        self.organizations = mommy.make(Organization, monitoring=self.monitoring, email='test@test.ru',
                                        inv_status='NTS', _quantity=10)
        # AND expert A account
        self.expertA = User.objects.create_user('expertA', 'experta@svobodainfo.org', 'password')
        self.expertA.groups.add(Group.objects.get(name=self.expertA.profile.expertA_group))
        # AND 'from' email
        self.from_email = config_value('EmailServer', 'DEFAULT_FROM_EMAIL')
        # AND organization page url
        self.url = reverse('exmo2010:organization_list', args=[self.monitoring.pk])

    @parameterized.expand([
        (u'Тема', u'Содержание', 'NTS'),
        ('Subject', 'Content', 'ALL'),
    ])
    def test_sending_emails(self, email_subject, email_content, invitation_status):
        # WHEN I am logged in as expertA
        self.client.login(username='expertA', password='password')
        # AND I submit email sending form
        resp = self.client.post(
            self.url,
            {
                'comment': [email_content],
                'subject': [email_subject],
                'inv_status': [invitation_status],
                'monitoring': ['%d' % self.monitoring.pk],
                'submit_invite': [''],
            },
            follow=True
        )
        # THEN response status_code is 200 (OK)
        self.assertEqual(resp.status_code, 200)
        # AND expert A should be redirected to the same url with get parameter and hash
        self.assertRedirects(resp, self.url + '?alert=success#all')
        # AND we should have 10 emails in our outbox
        self.assertEqual(len(mail.outbox), 10)
        # AND emails should have expected headers
        email = mail.outbox[0].message()
        self.assertEqual(email['From'].encode(), self.from_email)
        subject, encoding = decode_header(email['Subject'])[0]
        if encoding:
            subject = subject.decode(encoding)
        self.assertEqual(subject, email_subject)
        self.assertEqual(email['To'].encode(), self.organizations[0].email)
        # AND should have headers for Message Delivery Notification
        self.assertEqual(email['Disposition-Notification-To'].encode(), self.from_email)
        self.assertEqual(email['Return-Receipt-To'].encode(), self.from_email)
        self.assertEqual(email['X-Confirm-Reading-To'].encode(), self.from_email)
        # AND message ID should contain organizations invitation code
        match = re.search("<(?P<invitation_code>[\w\d]+)@(?P<host>[\w\d.-]+)>", email['Message-ID'].encode())
        invitation_code = match.group('invitation_code')
        self.assertIn(invitation_code, [org.inv_code for org in self.organizations])
        # AND invitation status should change from 'Not sent' to 'Sent'
        for org in Organization.objects.all():
            self.assertEqual(org.inv_status, 'SNT')
