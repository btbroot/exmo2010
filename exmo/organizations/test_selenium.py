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

from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from model_mommy import mommy
from nose.plugins.attrib import attr

from core.test_utils import BaseSeleniumTestCase
from exmo2010.models import Organization


@attr('selenium')
class OrgEmailFormValidationTestCase(BaseSeleniumTestCase):
    # exmo2010:organization_list

    # Submit email button should be disabled if required inputs are not provided.
    
    def setUp(self):
        # GIVEN organization with email
        org = mommy.make(Organization, email='email@mail.ru')

        # AND I am logged in as expert A
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.login('expertA', 'password')

        # AND i am on organization list page
        self.get(reverse('exmo2010:organization_list', args=[org.monitoring.pk]))

        # AND i click on 'send mail' tab
        self.find('a[href="#send_mail"]').click()

    def test_email_form_validation(self):
        # INITIALLY submit button should be disabled
        self.assertDisabled('input[name="submit_mail"]')

        # WHEN i type message subject in form
        self.find('#id_subject').send_keys('Subject')

        # THEN submit button should stay disabled
        self.assertDisabled('input[name="submit_mail"]')

        # WHEN i type message body in form
        with self.frame('iframe'):
            self.find('body').send_keys('Content')

        # THEN submit button should stay disabled
        self.assertDisabled('input[name="submit_mail"]')

        # WHEN i check destination "inactive orgs" checkbox
        self.find('#id_dst_orgs_inact').click()

        # THEN submit button should become enabled
        self.assertEnabled('input[name="submit_mail"]')
