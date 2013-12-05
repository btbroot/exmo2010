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
from urlparse import urlparse

from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.urlresolvers import reverse
from model_mommy import mommy

from core.test_utils import BaseSeleniumTestCase
from exmo2010.models import *


class OrganizationSendMailPageTestCase(BaseSeleniumTestCase):
    # Scenario: Test organization page
    submit_button = 'div.content input[type="submit"]'

    def setUp(self):
        # GIVEN expert A account
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.groups.add(Group.objects.get(name=expertA.profile.expertA_group))
        # AND monitoring
        self.monitoring = mommy.make(Monitoring)
        # AND organization with email connected to monitoring
        self.organization = mommy.make(Organization, monitoring=self.monitoring, email='email@mail.ru')
        # AND 'send mail' page url
        self.url = reverse('exmo2010:organization_list', args=[self.monitoring.pk])

    def test_warning_message_at_send_mail_page(self):
        # WHEN I login as expert A
        self.login('expertA', 'password')
        # AND I get the page
        self.get(self.url)
        # AND click on 'send mail' tab
        tab = self.find('a[href="#send_mail"]')
        tab.click()
        # AND submit form
        submit = self.find(self.submit_button)
        submit.click()
        # THEN warning window should be displayed
        warning = self.wait_visible('div.warning')
        self.assertEqual(warning, True)

    def test_success_message_at_send_mail_page(self):
        # WHEN I login as expert A
        self.login('expertA', 'password')
        # AND I get the page
        self.get(self.url)
        # AND click on 'send mail' tab
        tab = self.find('a[href="#send_mail"]')
        tab.click()
        # AND post form data
        subject = self.find('#id_subject')
        subject.send_keys(['Subject'])
        content = self.find('#cke_contents_id_comment iframe')
        content.send_keys(['Content'])
        # AND submit form
        submit = self.find(self.submit_button)
        submit.click()
        # THEN mail outbox should have 1 email
        self.assertEqual(len(mail.outbox), 1)
        # AND current url should contain expected path
        current_url = urlparse(self.webdrv.current_url)
        self.assertEqual(current_url.path, self.url)
        # AND current url should contain expected query parameter
        self.assertEqual(current_url.query, 'alert=success')
        # AND current url should contain expected hash
        self.assertEqual(current_url.fragment, 'all')
        # AND success window should be displayed
        success = self.wait_visible('p.success')
        self.assertEqual(success, True)
