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
from datetime import date

from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from model_mommy import mommy

from core.test_utils import BaseSeleniumTestCase
from exmo2010.models import *


class CertificateOrderTestCase(BaseSeleniumTestCase):
    # Scenario: Checking certificate ordering
    name_element_id = '#id_0-name'
    wishes_element_id = '#id_0-wishes'
    email_element_id = '#id_0-email'
    for_whom_element_id = '#id_0-for_whom'
    zip_code_element_id = '#id_0-zip_code'
    address_element_id = '#id_0-address'
    submit_button = 'div.buttons_group > div > input'

    def setUp(self):
        self.url = reverse('exmo2010:certificate_order')

        # GIVEN expert B account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.groups.add(Group.objects.get(name=expertB.profile.expertB_group))

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
        # AND parameter at monitoring
        self.parameter = mommy.make(
            Parameter,
            monitoring=self.monitoring,
            weight=1,
        )
        # AND score for parameter
        self.score = mommy.make(
            Score,
            task=self.task,
            parameter=self.parameter,
            found=0,
        )
        # AND organization representative account
        org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        org.groups.add(Group.objects.get(name=org.profile.organization_group))
        org.profile.organization.add(self.organization)
        org.first_name = 'Org'
        org.save()

        # AND org is logged in
        self.login('org', 'password')

    def test_org_goes_to_certificate_order_page(self):
        # WHEN org get certificate page
        self.get(self.url)
        # AND get elements
        name = self.find(self.name_element_id)
        wishes = self.find(self.wishes_element_id)
        email = self.find(self.email_element_id)
        for_whom = self.find(self.for_whom_element_id)
        zip_code = self.find(self.zip_code_element_id)
        address = self.find(self.address_element_id)
        # THEN we should see only email field
        self.assertEqual(name.is_displayed(), False)
        self.assertEqual(wishes.is_displayed(), False)
        self.assertEqual(email.is_displayed(), True)
        self.assertEqual(for_whom.is_displayed(), False)
        self.assertEqual(zip_code.is_displayed(), False)
        self.assertEqual(address.is_displayed(), False)

    def test_submit_form_with_empty_email_field(self):
        # WHEN org get certificate page
        self.get(self.url)
        # AND submit form with empty email field
        email = self.find(self.email_element_id)
        email.clear()
        submit = self.find(self.submit_button)
        submit.click()
        # THEN we should see warning message
        warning = self.find('p.warning')
        self.assertEqual(warning.is_displayed(), True)

    def test_submit_form_with_incorrect_email_field(self):
        # WHEN org get certificate page
        self.get(self.url)
        # AND submit form with incorrect email
        email = self.find(self.email_element_id)
        email.clear()
        email.send_keys('incorrectemail.org')
        submit = self.find(self.submit_button)
        submit.click()
        # THEN we also should see warning message
        warning = self.find('p.warning')
        self.assertEqual(warning.is_displayed(), True)

    def test_submit_form_with_correct_email_field(self):
        # WHEN org get certificate page
        self.get(self.url)
        # AND submit form with correct email
        email = self.find(self.email_element_id)
        email.clear()
        email.send_keys('correct@email.org')
        submit = self.find(self.submit_button)
        submit.click()
        # THEN we should see next page
        # WHEN org click to previous button
        prev = self.find('#previous_form')
        prev.click()
        # THEN we sould see previous page with inputs data
        email_value = self.find(self.email_element_id).get_attribute('value')
        self.assertEqual(email_value, 'correct@email.org')

    def test_click_to_certificate_for_radio(self):
        # WHEN org get certificate page
        self.get(self.url)
        # AND click to 'certificate for' radio button
        certificate_for_button_0 = self.find('input[name="0-certificate_for"][value="0"]')
        certificate_for_button_1 = self.find('input[name="0-certificate_for"][value="1"]')
        certificate_for_button_1.click()
        cert1 = certificate_for_button_0.is_selected()
        self.assertEqual(cert1, False)
        cert2 = certificate_for_button_1.is_selected()
        self.assertEqual(cert2, True)
        # THEN we should see 'name' and 'wishes' fields
        name = self.find(self.name_element_id)
        wishes = self.find(self.wishes_element_id)
        self.assertEqual(name.is_displayed(), True)
        self.assertEqual(wishes.is_displayed(), True)

    def test_click_to_delivery_method_radio(self):
        # WHEN org get certificate page
        self.get(self.url)
        # AND click to 'delivery method' radio button
        delivery_method_button_0 = self.find('input[name="0-delivery_method"][value="0"]')
        delivery_method_button_1 = self.find('input[name="0-delivery_method"][value="1"]')
        delivery_method_button_1.click()
        deliv1 = delivery_method_button_0.is_selected()
        self.assertEqual(deliv1, False)
        deliv2 = delivery_method_button_1.is_selected()
        self.assertEqual(deliv2, True)
        # THEN we should see 'for whom', 'zip code' and 'address' fields
        for_whom = self.find(self.for_whom_element_id)
        zip_code = self.find(self.zip_code_element_id)
        address = self.find(self.address_element_id)
        self.assertEqual(for_whom.is_displayed(), True)
        self.assertEqual(zip_code.is_displayed(), True)
        self.assertEqual(address.is_displayed(), True)
        # AND 'email' field should disappear
        email = self.find(self.email_element_id)
        self.assertEqual(email.is_displayed(), False)

    def test_submit_two_forms(self):
        # WHEN org get certificate page
        self.get(self.url)
        # AND submit form at the fist page
        certificate_for_button_1 = self.find('input[name="0-certificate_for"][value="1"]')
        certificate_for_button_1.click()
        delivery_method_button_1 = self.find('input[name="0-delivery_method"][value="1"]')
        delivery_method_button_1.click()
        name = self.find(self.name_element_id)
        for_whom = self.find(self.for_whom_element_id)
        zip_code = self.find(self.zip_code_element_id)
        address = self.find(self.address_element_id)
        name.send_keys('Name Surname')
        for_whom.send_keys('Name Surname')
        zip_code.send_keys('123456')
        address.send_keys('St.Peterburg, Nevsky st., 1')
        submit = self.find(self.submit_button)
        submit.click()
        # AND submit form at the second page
        submit = self.find('input[type="submit"]')
        submit.click()
        # THEN we should see success message
        success = self.find('div.success')
        self.assertEqual(success.is_displayed(), True)
