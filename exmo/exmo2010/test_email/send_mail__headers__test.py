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
from django.core.mail.utils import DNS_NAME
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from livesettings import config_get
from model_mommy import mommy

from exmo2010.models import Organization


class SendMailHeadersTestCase(TestCase):
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
