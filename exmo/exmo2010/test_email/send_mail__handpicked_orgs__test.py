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
from django.core import mail
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy
from nose_parameterized import parameterized

from exmo2010.models import Organization, Monitoring, PUB


class HandpickedOrgEmailTestCase(TestCase):
    # exmo2010:send_mail

    # When form is submitted with handpicked organizations, email messages should be sent only to
    # those orgs, which was handpicked and match filters, selected with form.

    def setUp(self):
        # GIVEN published monitoring
        self.monitoring = mommy.make(Monitoring, status=PUB)

        # AND 4 organizations of different inv_status
        self.org_nts = mommy.make(Organization, monitoring=self.monitoring, email='nts@test.ru', inv_status='NTS')
        self.org_snt = mommy.make(Organization, monitoring=self.monitoring, email='snt@test.ru', inv_status='SNT')
        self.org_rd = mommy.make(Organization, monitoring=self.monitoring, email='rd@test.ru', inv_status='RD')
        self.org_rgs = mommy.make(Organization, monitoring=self.monitoring, email='rgs@test.ru', inv_status='RGS')
        # AND 2 active ('ACT' inv_status) organizations
        self.org_act1 = mommy.make(Organization, monitoring=self.monitoring, email='act1@test.ru', inv_status='ACT')
        self.org_act2 = mommy.make(Organization, monitoring=self.monitoring, email='act2@test.ru', inv_status='ACT')

        # AND I am logged in as expertA
        self.expertA = User.objects.create_user('expertA', 'experta@svobodainfo.org', 'password')
        self.expertA.groups.add(Group.objects.get(name=self.expertA.profile.expertA_group))
        self.client.login(username='expertA', password='password')

        self.url = reverse('exmo2010:send_mail', args=[self.monitoring.pk])

    @parameterized.expand([
        ('dst_orgs_noreg', ['nts']),   # 'snt' and 'rd' organizations should be omitted
        ('dst_orgs_inact', []),        # 'rgs' organization should be omitted
        ('dst_orgs_activ', ['act1']),  # 'act2' organization should be omitted
    ])
    def test_send_org_emails(self, selected_orgs, expected_receivers):
        # WHEN I hand-pick 2 organizations: nts and act1
        handpicked_orgs = [self.org_nts.pk, self.org_act1.pk]
        post_data = {'comment': 'txt', 'subject': 'subj', selected_orgs: '1', 'handpicked_orgs': handpicked_orgs}

        # AND I submit email form
        response = self.client.post(self.url, post_data, follow=True)

        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND i should be redirected to the mail history list page
        self.assertRedirects(response, reverse('exmo2010:send_mail_history', args=[self.monitoring.pk]))

        # AND email messages should be sent to expected receivers
        receivers = set(tuple(m.to) for m in mail.outbox)
        expected_receivers = set((addr + '@test.ru',) for addr in expected_receivers)
        self.assertEqual(receivers, expected_receivers)
