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
import re
import time
from email.header import decode_header

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.crypto import salted_hmac
from livesettings import config_value
from model_mommy import mommy
from nose_parameterized import parameterized

from core.mail_tests import LocmemBackendTests
from custom_comments.models import CommentExmo
from exmo2010.models import *


class OrgCreateTestCase(TestCase):
    # test adding organization using form

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND i am logged in as expertA:
        self.expertA = User.objects.create_user('expertA', 'A@ya.ru', 'password')
        self.expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

    def test_add_org(self):
        formdata = {'org-name_en': 'ooo', 'org-monitoring': 99, 'submit_add': True}
        # WHEN I submit organization add form
        response = self.client.post(reverse('exmo2010:organization_list', args=[self.monitoring.pk]), formdata)
        # THEN new organization shoud get created in database
        orgs = Organization.objects.values_list('name', 'monitoring_id')
        self.assertEqual(list(orgs), [('ooo', self.monitoring.pk)])
        # AND response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)


class DuplicateOrgCreationTestCase(TestCase):
    # SHOULD return validation error if organization with already existing name is added

    def setUp(self):
        # GIVEN monitoring with organization
        self.monitoring = mommy.make(Monitoring)
        self.org = mommy.make(Organization, name='org', monitoring=self.monitoring)

        # AND i am logged in as expertA:
        self.expertA = User.objects.create_user('expertA', 'A@ya.ru', 'password')
        self.expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

    def test_error_on_duplicate(self):
        formdata = {'org-name_en': self.org.name, 'org-monitoring': 99, 'submit_add': True}
        # WHEN I submit organization add form with existing name
        response = self.client.post(reverse('exmo2010:organization_list', args=[self.monitoring.pk]), formdata)
        # THEN no new orgs shoud get created in database
        self.assertEqual(list(Organization.objects.all()), [self.org])
        # AND response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND error message should say that such organization exists
        errors = {'__all__': [u'Organization with this Name [en] and Monitoring already exists.']}
        self.assertEqual(response.context['form'].errors, errors)


class OrganizationEditAccessTestCase(TestCase):
    # SHOULD allow only expertA to edit organization

    def setUp(self):
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

        self.url = reverse('exmo2010:organization_update', args=[self.monitoring.pk, self.organization.pk])

    def test_anonymous_org_edit_get(self):
        # WHEN anonymous user gets organization edit page
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
        resp = self.client.get(url, follow=True)
        # THEN redirect to login page
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
        # THEN response status_code should be 200 (OK)
        self.assertEqual(resp.status_code, 200)
        # AND expert A should be redirected to the same url with get parameter and hash
        self.assertRedirects(resp, self.url + '?alert=success#all')
        # AND 10 emails should be sent
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


class OrganizationStatusRegisteredOnFirstRegisteredRepresentativeTestCase(TestCase):
    # Organization SHOULD change invitation status to 'registered' when first representative is registered.
    # Different organizations of single representative SHOULD NOT affect status of each other.

    def setUp(self):
        site = Site.objects.get_current()
        content_type = ContentType.objects.get_for_model(Score)

        # GIVEN organization with 'read' invitation status in interaction monitoring
        self.org_read = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION, inv_status='RD')
        # AND organization with 'activated' invitation status in published monitoring
        org_activated = mommy.make(Organization, monitoring__status=MONITORING_PUBLISHED, inv_status='ACT')
        # AND score of org_activated
        param = mommy.make(Parameter, monitoring=org_activated.monitoring, weight=1)
        score = mommy.make(Score, task__status=Task.TASK_APPROVED, task__organization=org_activated, parameter=param)
        # AND orguser, representative of org_activated
        orguser = User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        orguser.profile.organization = [org_activated]
        # AND orguser comment for score of org_activated
        mommy.make(CommentExmo, content_type=content_type, object_pk=score.pk, user=orguser, site=site)
        # AND I am logged in as orguser
        self.client.login(username='user', password='password')

    def test_registered_status(self):
        # WHEN I submit form with invitation code of org_read
        self.client.post(reverse('exmo2010:settings'), {'invitation_code': self.org_read.inv_code})
        #THEN org_read status should change to 'registered'
        new_status = Organization.objects.get(pk=self.org_read.pk).inv_status
        self.assertEqual(new_status, 'RGS')


class OrganizationStatusActivatedOnFirstCommentTestCase(TestCase):
    # Organization SHOULD change invitation status to 'activated'
    # when representative posts comment to relevant task's score.

    def setUp(self):
        # GIVEN organization in interaction monitoring
        self.org = mommy.make(Organization, name='org2', monitoring__status=MONITORING_INTERACTION, inv_status='RGS')
        # AND corresponding parameter, and score for organization
        param = mommy.make(Parameter, monitoring=self.org.monitoring, weight=1)
        self.score = mommy.make(Score, task__status=Task.TASK_APPROVED, task__organization=self.org, parameter=param)
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        orguser.groups.add(Group.objects.get(name=orguser.profile.organization_group))
        orguser.profile.organization = [self.org]
        # AND I am logged in as organization representative
        self.client.login(username='orguser', password='password')

    def test_activated_status(self):
        # WHEN I post first comment
        key_salt = "django.contrib.forms.CommentSecurityForm"
        timestamp = str(int(time.time()))
        content_type = ContentType.objects.get_for_model(Score)
        content_type = '.'.join([content_type.app_label, content_type.model])
        value = "-".join([content_type, str(self.score.pk), timestamp])
        data = {
            'status': '0',
            'comment': 'Comment',
            'timestamp': timestamp,
            'object_pk': self.score.pk,
            'security_hash': salted_hmac(key_salt, value).hexdigest(),
            'content_type': content_type,
        }
        self.client.post(reverse('login-required-post-comment'), data)
        # THEN organization invitation status should change to 'activated' ('ACT')
        self.assertEqual(Organization.objects.get(pk=self.org.pk).inv_status, 'ACT')
