# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2013 Al Nikolov
# Copyright 2015-2016 IRSI LTD
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
from django.core import mail
from django.core.urlresolvers import reverse
from model_mommy import mommy
from nose.plugins.attrib import attr

from core.test_utils import BaseSeleniumTestCase
from exmo2010.models import Parameter, Organization, Score, Task, OrgUser
from exmo2010.models.monitoring import Monitoring, MONITORING_PUBLISHED


@attr('selenium')
class ContactsFormTestCase(BaseSeleniumTestCase):
    # exmo2010:index

    # Submitting valid contacts form should display success message and send email.
    # Submitting invalid form should display errors.

    def test_default_visible_formfields(self):
        # WHEN i get index page.
        self.get(reverse('exmo2010:index'))

        # INITIALLY validation erros should be hidden.
        self.assertHidden('div.err_required')
        self.assertHidden('div.err_invalid')

        # WHEN i click submit button with empty contacts message form.
        self.find('#submit_message').click()
        # THEN required error messages should become visible.
        self.assertVisible('div.err_required')

        # WHEN i fill all inputs, bit with invalid email.
        self.find('#id_name').send_keys('name')
        self.find('#id_email').send_keys('invalid')
        self.find('#id_text').send_keys('txt')

        # AND i click submit button.
        self.find('#submit_message').click()
        # THEN ivalid error message should become visible.
        self.assertVisible('div.err_invalid')

        # WHEN i fill valid email.
        self.find('#id_email').send_keys('correct@email.org')
        # AND i click submit button.
        self.find('#submit_message').click()

        # THEN all validation erros should become hidden.
        self.assertHidden('div.err_required')
        self.assertHidden('div.err_invalid')

        # AND success message should become visible.
        self.assertVisible('div.submit_result_message.success')

        # AND there should be 2 email messages in the outbox.
        self.assertEqual(len(mail.outbox), 2)


@attr('selenium')
class CertificateOrderTestCase(BaseSeleniumTestCase):
    # Check certificate ordering page
    name_element_id = '#id_name'
    wishes_element_id = '#id_wishes'
    email_element_id = '#id_email'
    for_whom_element_id = '#id_for_whom'
    zip_code_element_id = '#id_zip_code'
    address_element_id = '#id_address'
    submit_button = 'div.buttons_group > div > input'

    def setUp(self):
        # GIVEN expert B account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.groups.add(Group.objects.get(name=expertB.profile.expertB_group))

        # AND published monitoring
        monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED, publish_date=date.today())
        # AND organzation at this monitoring
        org = mommy.make(Organization, name=u'ы', monitoring=monitoring)
        # AND task for expert B
        task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_APPROVED)
        # AND parameter at monitoring
        parameter = mommy.make(Parameter, monitoring=monitoring, weight=1)
        # AND score for parameter
        mommy.make(Score, task=task, parameter=parameter, found=0)
        # AND organization representative account
        orguser = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        orguser.groups.add(Group.objects.get(name=orguser.profile.organization_group))
        mommy.make(OrgUser, organization=org, userprofile=orguser.profile)
        orguser.first_name = 'Org'
        orguser.save()

        # NOTE: pop message about task assignment to expertB
        # TODO: get rid of this automatic email on Task creation, move to the view
        mail.outbox.pop()

        # AND i am logged in as org representative
        self.login('org', 'password')
        # AND i open certificate page
        self.get(reverse('exmo2010:certificate_order'))

    def test_default_visible_formfields(self):
        # only email field should be visible
        self.assertVisible(self.email_element_id)
        self.assertHidden(self.name_element_id)
        self.assertHidden(self.wishes_element_id)
        self.assertHidden(self.for_whom_element_id)
        self.assertHidden(self.zip_code_element_id)
        self.assertHidden(self.address_element_id)

    def test_submit_form_with_empty_email_field(self):
        # WHEN i submit form with empty email field
        self.find(self.email_element_id).clear()
        self.find(self.submit_button).click()
        # THEN error message should be displayed
        self.assertVisible('div.email_group ul.errorlist li')

    def test_submit_form_with_incorrect_email_field(self):
        # WHEN i submit form with incorrect email
        self.find(self.email_element_id).clear()
        self.find(self.email_element_id).send_keys('incorrectemail.org')
        self.find(self.submit_button).click()
        # THEN error message should be displayed
        self.assertVisible('div.email_group ul.errorlist li')

    def test_submit_form_with_correct_email_field(self):
        # WHEN i enter some valid email
        self.find(self.email_element_id).clear()
        self.find(self.email_element_id).send_keys('correct@email.org')
        # AND submit form
        self.find(self.submit_button).click()
        # THEN next page should be opened with 'back' link
        self.assertVisible('#previous_form')
        # WHEN i click 'back' link
        self.find('#previous_form').click()
        # THEN previous page should be shown with data enetered before
        self.assertVisible(self.email_element_id)
        email_value = self.find(self.email_element_id).get_attribute('value')
        self.assertEqual(email_value, 'correct@email.org')

    def test_click_addressee_radio(self):
        # WHEN i click 'addressee' radio button
        addressee_0 = self.find('input[name="addressee"][value="org"]')
        addressee_1 = self.find('input[name="addressee"][value="user"]')
        addressee_1.click()
        self.assertEqual(addressee_0.is_selected(), False)
        self.assertEqual(addressee_1.is_selected(), True)
        # THEN 'name' and 'wishes' fields should get visible
        self.assertVisible(self.name_element_id)
        self.assertVisible(self.wishes_element_id)

    def test_click_to_delivery_method_radio(self):
        # WHEN i click 'delivery method' radio button
        delivery_method_0 = self.find('input[name="delivery_method"][value="email"]')
        delivery_method_1 = self.find('input[name="delivery_method"][value="post"]')
        delivery_method_1.click()
        self.assertEqual(delivery_method_0.is_selected(), False)
        self.assertEqual(delivery_method_1.is_selected(), True)
        # THEN 'for whom', 'zip code' and 'address' fields should get visible
        self.assertVisible(self.for_whom_element_id)
        self.assertVisible(self.zip_code_element_id)
        self.assertVisible(self.address_element_id)
        # AND 'email' field should disappear
        self.assertHidden(self.email_element_id)

    def test_submit_two_forms(self):
        # WHEN i fill form properly
        self.find('input[name="addressee"][value="user"]').click()
        self.find('input[name="delivery_method"][value="post"]').click()
        self.find(self.name_element_id).send_keys('Name Surname')
        self.find(self.for_whom_element_id).send_keys('Name Surname')
        self.find(self.zip_code_element_id).send_keys('123456')
        self.find(self.address_element_id).send_keys('St.Peterburg, Nevsky st., 1')
        # AND submit form
        self.find(self.submit_button).click()
        # AND submit confirmation form at the second page
        self.assertVisible('#confirm')
        self.find('#confirm').click()
        # THEN success message should be displayed
        self.assertVisible('div.success')
        # AND there should be 1 email message in the outbox
        self.assertEqual(len(mail.outbox), 1)

    def test_browser_back_after_bad_filter(self):
        # WHEN I submit filter with incorrect organization name
        self.find('#id_name_filter').send_keys('!@#&')
        self.find('form.filter input[type="submit"]').click()
        # THEN warning message should be displayed
        self.assertVisible('p.warning')
        # AND submit button should be disabled
        self.assertDisabled(self.submit_button)
        # WHEN I click on browser 'back' button
        self.webdrv.back()
        # THEN submit button should be visible
        self.assertVisible(self.submit_button)
        # WHEN I submit first certificate form
        self.find(self.submit_button).click()
        # AND submit second certificate form
        self.assertVisible('#confirm')
        self.find('#confirm').click()
        # THEN success message should be displayed
        self.assertVisible('div.success')
        # AND there should be 1 email message in the outbox
        self.assertEqual(len(mail.outbox), 1)
