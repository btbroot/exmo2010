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
from django.core import mail
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy
from nose_parameterized import parameterized

from custom_comments.models import CommentExmo
from exmo2010.models import Organization, Monitoring, Score, PUB, OrgUser, Task


class SelectiveOrgUserEmailTestCase(TestCase):
    # exmo2010:send_mail

    # Email messages should be sent only to those orgusers, which was selected in form.
    # Status of the users in other monitorings should not affect selection filter.

    def setUp(self):
        content_type = ContentType.objects.get_for_model(Score)

        # GIVEN 2 PUBLISHED monitorings
        self.monitoring = mommy.make(Monitoring, status=PUB)
        self.monitoring_other = mommy.make(Monitoring, status=PUB)

        # AND organization in monitoring
        self.org_rgs = mommy.make(Organization, monitoring=self.monitoring, email='rgs@test.ru', inv_status='RGS')

        # AND organization in monitoring_other
        self.org_other = mommy.make(Organization, monitoring=self.monitoring_other, email='rgs_other@test.ru', inv_status='RGS')

        # AND user, unseen representative of organization org_rgs, but seen in org_other
        self.orguser_unseen = User.objects.create_user('orguser_unseen', 'unseen@test.ru', 'password')
        mommy.make(OrgUser, organization=self.org_rgs, userprofile=self.orguser_unseen.profile, seen=False)
        mommy.make(OrgUser, organization=self.org_other, userprofile=self.orguser_unseen.profile, seen=True)

        # AND inactive representative of organization org_rgs, but active in org_other
        self.orguser_inactive = User.objects.create_user('orguser_inactive', 'inactive@test.ru', 'password')
        mommy.make(OrgUser, organization=self.org_rgs, userprofile=self.orguser_inactive.profile)
        mommy.make(OrgUser, organization=self.org_other, userprofile=self.orguser_inactive.profile)

        # AND active representative of organization org_rgs, but inactive in org_other
        self.orguser_active = User.objects.create_user('orguser_active', 'active@test.ru', 'password')
        mommy.make(OrgUser, organization=self.org_rgs, userprofile=self.orguser_active.profile)
        mommy.make(OrgUser, organization=self.org_other, userprofile=self.orguser_active.profile)

        # AND comment of active representative in org_rgs
        task = mommy.make(Task, organization=self.org_rgs, status=Task.TASK_APPROVED)
        score = mommy.make(Score, task=task, parameter__monitoring=self.monitoring)
        mommy.make(CommentExmo, object_pk=score.pk, content_type=content_type, user=self.orguser_active)

        # AND comment of inactive representative in org_other
        task = mommy.make(Task, organization=self.org_other, status=Task.TASK_APPROVED)
        score = mommy.make(Score, task=task, parameter__monitoring=self.monitoring_other)
        mommy.make(CommentExmo, object_pk=score.pk, content_type=content_type, user=self.orguser_inactive)

        # AND I am logged in as expertA
        self.expertA = User.objects.create_user('expertA', 'experta@svobodainfo.org', 'password')
        self.expertA.groups.add(Group.objects.get(name=self.expertA.profile.expertA_group))
        self.client.login(username='expertA', password='password')

        self.url = reverse('exmo2010:send_mail', args=[self.monitoring.pk])

    @parameterized.expand([
        ('dst_orgusers_inact', {('inactive@test.ru',)}),
        ('dst_orgusers_activ', {('active@test.ru',)}),
        ('dst_orgusers_unseen', {('unseen@test.ru',)}),
    ])
    def test_send_orguser_emails(self, selected_orgusers, expected_receivers):
        post_data = {'comment': u'Содержание', 'subject': u'Тема', selected_orgusers: '1'}

        # WHEN I submit email form
        response = self.client.post(self.url, post_data, follow=True)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND i should be redirected to the mail history list page
        self.assertRedirects(response, reverse('exmo2010:send_mail_history', args=[self.monitoring.pk]))

        # AND email messages should be sent to expected receivers
        receivers = set(tuple(m.to) for m in mail.outbox)
        self.assertEqual(receivers, expected_receivers)
