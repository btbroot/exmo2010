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
from cStringIO import StringIO

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import mail
from django.core.mail.utils import DNS_NAME
from django.core.urlresolvers import reverse
from django.test import TestCase
from livesettings import config_get, config_value
from mock import Mock
from model_mommy import mommy
from nose_parameterized import parameterized


from core.utils import UnicodeReader
from custom_comments.models import CommentExmo
from exmo2010.models import (
    Monitoring, Organization, Task, Parameter, Score, ObserversGroup, MONITORING_INTERACTION, MONITORING_PUBLISHED
)
from .views import RepresentativesView


class OrgCreateTestCase(TestCase):
    # exmo2010:organizations_add

    # test adding organization using form

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND I am logged in as expertA:
        self.expertA = User.objects.create_user('expertA', 'A@ya.ru', 'password')
        self.expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

    def test_add_org(self):
        formdata = {'name_en': 'ooo'}
        # WHEN I submit organization add form
        response = self.client.post(reverse('exmo2010:organizations_add', args=[self.monitoring.pk]), formdata)
        # THEN response status_code should be 302 (Redirect)
        self.assertEqual(response.status_code, 302)
        # AND new organization should get created in database
        orgs = Organization.objects.values_list('name', 'monitoring_id')
        self.assertEqual(list(orgs), [('ooo', self.monitoring.pk)])


class DuplicateOrgCreationTestCase(TestCase):
    # exmo2010:organizations_add

    # Should return validation error if organization with already existing name is added

    def setUp(self):
        # GIVEN monitoring with organization
        self.monitoring = mommy.make(Monitoring)
        self.org = mommy.make(Organization, name='org', monitoring=self.monitoring)

        # AND i am logged in as expertA:
        self.expertA = User.objects.create_user('expertA', 'A@ya.ru', 'password')
        self.expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

    def test_error_on_duplicate(self):
        formdata = {'name_en': self.org.name}
        # WHEN I submit organization add form with existing name
        response = self.client.post(reverse('exmo2010:organizations_add', args=[self.monitoring.pk]), formdata)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND no new orgs should get created in database
        self.assertEqual(list(Organization.objects.all()), [self.org])
        # AND error message should say that such organization exists
        errors = {'__all__': [u'Organization with this Name [en] and Monitoring already exists.']}
        self.assertEqual(response.context['form'].errors, errors)


class OrganizationEditAccessTestCase(TestCase):
    # Should allow only expertA to edit organization

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
        orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        orguser.profile.organization = [self.organization]
        # AND observer user
        observer = User.objects.create_user('observer', 'observer@svobodainfo.org', 'password')
        # AND observers group for monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=self.monitoring)
        obs_group.organizations = [self.organization]
        obs_group.users = [observer]

        self.url = reverse('exmo2010:organizations_update', args=[self.monitoring.pk, self.organization.pk])

    def test_anonymous_org_edit_get(self):
        # WHEN anonymous user gets organization edit page
        response = self.client.get(self.url, follow=True)
        # THEN he is redirected to login page
        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + self.url)

    @parameterized.expand([
        ('user', 403),
        ('orguser', 403),
        ('observer', 403),
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
        ('orguser',),
        ('observer',),
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
        self.orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        self.orguser.get_profile().organization = [self.organization]

    def test_anonymous_organizations_page_access(self):
        url = reverse('exmo2010:organizations', args=[self.monitoring.pk])
        # WHEN anonymous user get organizations page
        resp = self.client.get(url, follow=True)
        # THEN redirect to login page
        self.assertRedirects(resp, settings.LOGIN_URL + '?next=' + url)

    @parameterized.expand([
        ('user', 403),
        ('orguser', 403),
        ('expertB', 403),
        ('expertA', 200),
        ('admin', 200),
    ])
    def test_authenticated__user_organizations_page_access(self, username, response_code):
        url = reverse('exmo2010:organizations', args=[self.monitoring.pk])
        # WHEN user get organizations page
        self.client.login(username=username, password='password')
        resp = self.client.get(url)
        # THEN only admin and expert A have access
        self.assertEqual(resp.status_code, response_code)


class SelectiveOrgEmailTestCase(TestCase):
    # exmo2010:send_mail

    # Email messages should be sent only to those receivers, which was selected in form.

    def setUp(self):
        content_type = ContentType.objects.get_for_model(Score)

        # GIVEN published monitoring
        self.monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)

        # AND 5 organizations of different inv_status
        self.org_nts = mommy.make(Organization, monitoring=self.monitoring, email='nts@test.ru', inv_status='NTS')
        self.org_snt = mommy.make(Organization, monitoring=self.monitoring, email='snt@test.ru', inv_status='SNT')
        self.org_rd = mommy.make(Organization, monitoring=self.monitoring, email='rd@test.ru', inv_status='RD')
        self.org_rgs = mommy.make(Organization, monitoring=self.monitoring, email='rgs@test.ru', inv_status='RGS')
        self.org_act = mommy.make(Organization, monitoring=self.monitoring, email='act@test.ru', inv_status='ACT')

        # AND inactive representative of organization org_rgs
        self.orguser_inactive = User.objects.create_user('orguser_inactive', 'inactive@test.ru', 'password')
        self.orguser_inactive.get_profile().organization = [self.org_rgs]

        # AND active representative of organization org_rgs
        self.orguser_active = User.objects.create_user('orguser_active', 'active@test.ru', 'password')
        self.orguser_active.get_profile().organization = [self.org_rgs]

        # AND comment of active representative
        task = mommy.make(Task, organization=self.org_rgs, status=Task.TASK_APPROVED)
        score = mommy.make(Score, task=task, parameter__monitoring=self.monitoring)
        mommy.make(CommentExmo, object_pk=score.pk, content_type=content_type, user=self.orguser_active)

        # AND server email address
        self.server_address = config_value('EmailServer', 'DEFAULT_FROM_EMAIL')

        # AND I am logged in as expertA
        self.expertA = User.objects.create_user('expertA', 'experta@svobodainfo.org', 'password')
        self.expertA.groups.add(Group.objects.get(name=self.expertA.profile.expertA_group))
        self.client.login(username='expertA', password='password')

        self.url = reverse('exmo2010:send_mail', args=[self.monitoring.pk])

    @parameterized.expand([
        ('dst_orgs_noreg', {'nts', 'snt', 'rd'}),
        ('dst_orgs_inact', {'rgs'}),
        ('dst_orgs_activ', {'act'}),
    ])
    def test_send_org_emails(self, selected_orgs, expected_receivers):
        post_data = {'comment': u'Содержание', 'subject': u'Тема', selected_orgs: '1'}

        # WHEN I submit email form
        response = self.client.post(self.url, post_data, follow=True)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND i should be redirected to the organizations list page
        self.assertRedirects(response, reverse('exmo2010:organizations', args=[self.monitoring.pk]))

        # AND email messages should be sent to expected receivers
        receivers = set(tuple(m.to) for m in mail.outbox)
        expected_receivers = set((addr + '@test.ru',) for addr in expected_receivers)
        self.assertEqual(receivers, expected_receivers)

    @parameterized.expand([
        ('dst_orgusers_inact', {('inactive@test.ru',)}),
        ('dst_orgusers_activ', {('active@test.ru',)}),
    ])
    def test_send_orguser_emails(self, selected_orgusers, expected_receivers):
        post_data = {'comment': u'Содержание', 'subject': u'Тема', selected_orgusers: '1'}

        # WHEN I submit email form
        response = self.client.post(self.url, post_data, follow=True)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND i should be redirected to the organizations list page
        self.assertRedirects(response, reverse('exmo2010:organizations', args=[self.monitoring.pk]))

        # AND email messages should be sent to expected receivers
        receivers = set(tuple(m.to) for m in mail.outbox)
        self.assertEqual(receivers, expected_receivers)


class OrgEmailHeadersTestCase(TestCase):
    # exmo2010:send_mail

    # Email messages sent to organizations should have proper headers.

    def setUp(self):
        # GIVEN organization with 'NTS' inv_status
        self.org = mommy.make(Organization, email='nts@test.ru', inv_status='NTS')

        # AND I am logged in as expertA
        self.expertA = User.objects.create_user('expertA', 'experta@svobodainfo.org', 'password')
        self.expertA.groups.add(Group.objects.get(name=self.expertA.profile.expertA_group))
        self.client.login(username='expertA', password='password')

    def test_send_org_emails(self):
        url = reverse('exmo2010:send_mail', args=[self.org.monitoring.pk])
        post_data = {'comment': u'Содержание', 'subject': u'Тема', 'dst_orgs_noreg': '1'}
        server_address = config_get('EmailServer', 'DEFAULT_FROM_EMAIL')
        server_email_address = 'test@domain.com'
        server_address.update(u'Имя хоста <{}>'.format(server_email_address))

        # WHEN I submit email form
        response = self.client.post(url, post_data, follow=True)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND one email should be sent
        self.assertEqual(len(mail.outbox), 1)

        # AND email message should have expected headers
        message = mail.outbox[0]
        self.assertEqual(message.from_email, server_address)
        self.assertEqual(message.subject, u'Тема')
        self.assertEqual(message.to, [self.org.email])
        # AND should have headers for Message Delivery Notification and ID
        self.assertEqual(message.extra_headers['Disposition-Notification-To'], server_email_address)
        self.assertEqual(message.extra_headers['Return-Receipt-To'], server_email_address)
        self.assertEqual(message.extra_headers['X-Confirm-Reading-To'], server_email_address)
        self.assertEqual(message.extra_headers['Message-ID'], '<%s@%s>' % (self.org.inv_code, DNS_NAME))

        # TODO: move out this into new TestCase
        # AND invitation status should change from 'Not sent' to 'Sent'
        for org in Organization.objects.all():
            self.assertEqual(org.inv_status, 'SNT')


class OrganizationStatusRegisteredOnFirstRegisteredRepresentativeTestCase(TestCase):
    # Organization should change invitation status to 'registered' when first representative is registered.
    # Different organizations of single representative should not affect status of each other.

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
    # Organization should change invitation status to 'activated'
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
        url = reverse('exmo2010:post_score_comment', args=[self.score.pk])
        # WHEN I post first comment
        self.client.post(url, {'score_%s-comment' % self.score.pk: '123'})
        # THEN organization invitation status should change to 'activated' ('ACT')
        self.assertEqual(Organization.objects.get(pk=self.org.pk).inv_status, 'ACT')


class RepresentativesExportTestCase(TestCase):
    # exmo2010:representatives_export

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND there is 1 organization in monitoring
        org = mommy.make(Organization, monitoring=self.monitoring)
        # AND expert A account
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True
        # AND expert B with approved task in monitoring
        self.expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        self.expertB.profile.is_expertB = True
        task = mommy.make(Task, organization=org, user=self.expertB, status=Task.TASK_APPROVED)
        # AND parameter with score
        parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1)
        score = mommy.make(Score, task=task, parameter=parameter)
        # AND org representative
        orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        orguser.groups.add(Group.objects.get(name=orguser.profile.organization_group))
        orguser.profile.organization = [org]
        # AND comment from orguser
        mommy.make(CommentExmo, object_pk=score.pk, user=orguser)
        # AND I am logged in as expert A
        self.client.login(username='expertA', password='password')

    def test_csv(self):
        # WHEN I get csv-file from response for current monitoring
        monitoring = Monitoring.objects.get(pk=self.monitoring.pk)
        url = reverse('exmo2010:representatives_export', args=[monitoring.pk])
        response = self.client.get(url)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND csv-file should be valid
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        csv = UnicodeReader(StringIO(response.content))
        organization = monitoring.organization_set.all()[0]
        user = organization.userprofile_set.all()[0]
        for row in csv:
            if row[0].startswith('#'):
                continue
            # AND length of row should be 10
            self.assertEqual(len(row), 10)
            # AND row 1 should contain user activation status
            self.assertEqual(int(row[0]), int(user.user.is_active))
            # AND row 2 should contain organization name
            self.assertEqual(row[1], organization.name)
            # AND row 3 should contain user first name
            self.assertEqual(row[2], user.user.first_name)
            # AND row 4 should contain user last name
            self.assertEqual(row[3], user.user.last_name)
            # AND row 5 should contain user e-mail
            self.assertEqual(row[4], user.user.email)
            # AND row 6 should contain user phone number
            self.assertEqual(row[5], user.phone or '')
            # AND row 7 should contain user job title
            self.assertEqual(row[6], user.position or '')
            # AND row 8 should contain count of comments
            self.assertEqual(int(row[7]), 1)
            # AND row 9 should contain date of user registration
            self.assertEqual(row[8], user.user.date_joined.date().isoformat())
            # AND row 10 should contain date of user last login
            self.assertEqual(row[9], user.user.last_login.date().isoformat())


class RepresentativesFilterByOrganizationsTestCase(TestCase):
    # exmo2010:representatives

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND there are 2 organizations in monitoring
        self.org1 = mommy.make(Organization, monitoring=self.monitoring)
        self.org2 = mommy.make(Organization, monitoring=self.monitoring)
        # AND expert A account
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True
        # AND 1 representative connected to 2 organizations
        orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        orguser.groups.add(Group.objects.get(name=orguser.profile.organization_group))
        orguser.profile.organization = [self.org1, self.org2]
        # AND I am logged in as expert A
        self.client.login(username='expertA', password='password')

    def test_filter_query(self):
        url = reverse('exmo2010:representatives', args=[self.monitoring.pk])
        # WHEN I get filter by organizations
        response = self.client.get(url, {'full_name_or_email': '', 'organization': self.org1.pk})
        # THEN count of organizations should equal 1
        self.assertEqual(len(response.context['orgs']), 1)


class OrguserCommentCountTestCase(TestCase):
    # exmo2010:representatives

    # Displayed comment count of representatives should be calculated for each organization separately.

    def setUp(self):
        # GIVEN parameter in monitoring
        self.param = mommy.make(Parameter, weight=1)
        # AND 2 organizations in monitoring
        self.org1 = mommy.make(Organization, monitoring=self.param.monitoring, name='org1')
        self.org2 = mommy.make(Organization, monitoring=self.param.monitoring, name='org2')

        # AND 1 representative of 2 organizations
        orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        orguser.groups.add(Group.objects.get(name=orguser.profile.organization_group))
        orguser.profile.organization = [self.org1, self.org2]

        # AND score for each organization
        score_org1 = mommy.make(Score, task__organization=self.org1, parameter=self.param)
        score_org2 = mommy.make(Score, task__organization=self.org2, parameter=self.param)

        # AND 2 comments from representative for org1 score
        mommy.make(CommentExmo, object_pk=score_org1.pk, user=orguser)
        mommy.make(CommentExmo, object_pk=score_org1.pk, user=orguser)
        # AND 1 comment from representative for org2 score
        mommy.make(CommentExmo, object_pk=score_org2.pk, user=orguser)

        # AND expert A
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True

    def test_comment_count(self):
        # WHEN I get representatives page as expertA
        request = Mock(user=self.expertA, method='GET')
        response = RepresentativesView.as_view()(request, monitoring_pk=self.param.monitoring.pk)
        orgs = dict((org.name, org) for org in response.context_data['orgs'])
        # THEN org1 comments count should be 2
        self.assertEqual(orgs['org1'].users[0].comments.count(), 2)
        # AND org2 comments count should be 1
        self.assertEqual(orgs['org2'].users[0].comments.count(), 1)
