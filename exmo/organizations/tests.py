# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2016 IRSI LTD
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

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy
from mock import Mock

from .views import RepresentativesView
from custom_comments.models import CommentExmo
from exmo2010.models import (
    Monitoring, Organization, Task, Parameter, Score, INT, PUB, OrgUser
)


class OrgCreateTestCase(TestCase):
    # exmo2010:organization_add

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
        response = self.client.post(reverse('exmo2010:organization_add', args=[self.monitoring.pk]), formdata)
        # THEN response status_code should be 302 (Redirect)
        self.assertEqual(response.status_code, 302)
        # AND new organization should get created in database
        orgs = Organization.objects.values_list('name', 'monitoring_id')
        self.assertEqual(list(orgs), [('ooo', self.monitoring.pk)])


class DuplicateOrgCreationTestCase(TestCase):
    # exmo2010:organization_add

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
        response = self.client.post(reverse('exmo2010:organization_add', args=[self.monitoring.pk]), formdata)
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND no new orgs should get created in database
        self.assertEqual(list(Organization.objects.all()), [self.org])
        # AND error message should say that such organization exists
        errors = {'__all__': [u'Organization with this Name [en] and Monitoring already exists.']}
        self.assertEqual(response.context['form'].errors, errors)


class OrganizationStatusRegisteredOnFirstRegisteredRepresentativeTestCase(TestCase):
    # Organization should change invitation status to 'registered' when first representative is registered.
    # Different organizations of single representative should not affect status of each other.

    def setUp(self):
        site = Site.objects.get_current()
        content_type = ContentType.objects.get_for_model(Score)

        # GIVEN organization with 'read' invitation status in interaction monitoring
        self.org_read = mommy.make(Organization, monitoring__status=INT, inv_status='RD')
        # AND organization with 'activated' invitation status in published monitoring
        org_activated = mommy.make(Organization, monitoring__status=PUB, inv_status='ACT')
        # AND score of org_activated
        param = mommy.make(Parameter, monitoring=org_activated.monitoring, weight=1)
        score = mommy.make(Score, task__status=Task.TASK_APPROVED, task__organization=org_activated, parameter=param)
        # AND orguser, representative of org_activated
        orguser = User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        mommy.make(OrgUser, organization=org_activated, userprofile=orguser.profile)
        # AND orguser comment for score of org_activated
        mommy.make(CommentExmo, content_type=content_type, object_pk=score.pk, user=orguser, site=site)
        # AND I am logged in as orguser
        self.client.login(username='user', password='password')

    def test_registered_status(self):
        # WHEN I submit form with invitation code of org_read
        self.client.post(reverse('exmo2010:settings'), {'invitation_code': self.org_read.inv_code})
        # THEN org_read status should change to 'registered'
        new_status = Organization.objects.get(pk=self.org_read.pk).inv_status
        self.assertEqual(new_status, 'RGS')


class OrganizationStatusActivatedOnFirstCommentTestCase(TestCase):
    # Organization should change invitation status to 'activated'
    # when representative posts comment to relevant task's score.

    def setUp(self):
        # GIVEN organization in interaction monitoring
        self.org = mommy.make(Organization, name='org2', monitoring__status=INT, inv_status='RGS')
        # AND corresponding parameter, and score for organization
        param = mommy.make(Parameter, monitoring=self.org.monitoring, weight=1)
        self.score = mommy.make(Score, task__status=Task.TASK_APPROVED, task__organization=self.org, parameter=param)
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        orguser.groups.add(Group.objects.get(name=orguser.profile.organization_group))
        mommy.make(OrgUser, organization=self.org, userprofile=orguser.profile)
        # AND I am logged in as organization representative
        self.client.login(username='orguser', password='password')

    def test_activated_status(self):
        url = reverse('exmo2010:post_score_comment', args=[self.score.pk])
        # WHEN I post first comment
        self.client.post(url, {'score_%s-comment' % self.score.pk: '123'})
        # THEN organization invitation status should change to 'activated' ('ACT')
        self.assertEqual(Organization.objects.get(pk=self.org.pk).inv_status, 'ACT')


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
        mommy.make(OrgUser, organization=self.org1, userprofile=orguser.profile)
        mommy.make(OrgUser, organization=self.org2, userprofile=orguser.profile)
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
        mommy.make(OrgUser, organization=self.org1, userprofile=orguser.profile)
        mommy.make(OrgUser, organization=self.org2, userprofile=orguser.profile)

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
