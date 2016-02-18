# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013 Foundation "Institute for Information Freedom Development"
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
from urlparse import urlparse, parse_qs

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from model_mommy import mommy
from nose.plugins.attrib import attr

from core.test_utils import BaseSeleniumTestCase
from exmo2010.models import Organization
from exmo2010.views.send_mail import SendMailView


@attr('selenium')
class SendmailDisableButtonsTestCase(BaseSeleniumTestCase):
    # exmo2010:send_mail

    # "Preview" button should be disabled if required inputs are not provided.
    # "Submit" button should be disabled and hidden until email preview will not appear.

    def setUp(self):
        # GIVEN organization with email
        org = mommy.make(Organization, email='email@mail.ru')
        # AND expert A account
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND I am logged in as expert A
        self.login('expertA', 'password')

        # AND I am on send mail page
        self.get(reverse('exmo2010:send_mail', args=[org.monitoring.pk]))

    def test_sendmail_disable_preview(self):
        # INITIALLY preview button should be disabled
        self.assertDisabled('#preview_btn')

        # WHEN I type message subject in form
        self.find('#id_subject').send_keys('Subject')

        # THEN preview button should stay disabled
        self.assertDisabled('#preview_btn')

        # WHEN I type message body in form
        with self.frame('iframe'):
            self.find('body').send_keys('Content')

        # THEN preview button should stay disabled
        self.assertDisabled('#preview_btn')

        # WHEN I check destination "inactive orgs" checkbox
        self.find('#id_dst_orgs_inact').click()

        # THEN preview button should become enabled
        self.assertEnabled('#preview_btn')

    def test_sendmail_disable_submit(self):
        # INITIALLY submit button should be disabled and hidden
        self.assertDisabled('input[type="submit"]')
        self.assertHidden('input[type="submit"]')

        # WHEN I type message subject in form
        self.find('#id_subject').send_keys('Subject')

        # AND I type message body in form
        with self.frame('iframe'):
            self.find('body').send_keys('Content')

        # AND I check destination "not registered orgs" checkbox
        self.find('#id_dst_orgs_noreg').click()

        # THEN submit button should stay disabled and hidden
        self.assertDisabled('input[type="submit"]')
        self.assertHidden('input[type="submit"]')

        # WHEN I click on preview button
        self.find('#preview_btn').click()

        # THEN submit button should become enabled and visible
        self.assertEnabled('input[type="submit"]')
        self.assertVisible('input[type="submit"]')


@attr('selenium')
class OrganizationsDisableGroupactionTestCase(BaseSeleniumTestCase):
    # exmo2010:manage_orgs

    # "Create invite link" group-action button should be disabled if no checkbox ticked.

    def setUp(self):
        # GIVEN organization
        org = mommy.make(Organization)

        # AND I am logged in as expertA
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.login('expertA', 'password')

        # AND I am on "organizations" page
        self.get(reverse('exmo2010:manage_orgs', args=[org.monitoring.pk]))

    def test_sendmail_disable_submit(self):
        # INITIALLY group-action button should be disabled
        self.assertDisabled('#group_actions input.action')

        # WHEN I tick one organization checkbox
        self.find('table.base-table td input.group_actions').click()

        # THEN group-action button should become enabled
        self.assertEnabled('#group_actions input.action')

        # WHEN I untick organization checkbox
        self.find('table.base-table td input.group_actions').click()

        # THEN group-action button should become disabled
        self.assertDisabled('#group_actions input.action')


@attr('selenium')
class SelectedOrgsHideRecommendationsTestCase(BaseSeleniumTestCase):
    # exmo2010:manage_orgs

    # Selected orgs should have recommendations_hidden flag after group action.

    def setUp(self):
        # GIVEN monitoring with 3 organizations
        self.org1 = mommy.make(Organization, name='org1', recommendations_hidden=False)
        self.org2 = mommy.make(Organization, name='org2', monitoring=self.org1.monitoring, recommendations_hidden=False)
        self.org3 = mommy.make(Organization, name='org3', monitoring=self.org1.monitoring, recommendations_hidden=False)

        # AND I am logged in as expertA
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.login('expertA', 'password')

        # AND I am on "organizations" page
        self.get(reverse('exmo2010:manage_orgs', args=[self.org1.monitoring.pk]))

    def test_group_action(self):
        # WHEN I tick org2 and org3 checkbox
        self.find('#org_row_%s input.group_actions' % self.org2.pk).click()
        self.find('#org_row_%s input.group_actions' % self.org3.pk).click()

        # THEN "Hide recommendations" group-action button should become enabled
        self.assertEnabled('#group_actions input.hide_recommendations')

        # WHEN i click "Hide recommendations" button
        self.find('#group_actions input.hide_recommendations').click()

        # THEN success message should be displayed
        self.assertVisible('.success')

        # AND only org1 should have recommendations_hidden == False
        data = Organization.objects.values_list('name', 'recommendations_hidden')
        self.assertEqual(set(data), {('org1', False), ('org2', True), ('org3', True), })


@attr('selenium')
class OrganizationsSelectedOrgsInviteLinksTestCase(BaseSeleniumTestCase):
    # exmo2010:manage_orgs

    # Invite links should include codes of all selected organizations.
    # Invite links modal window should have proper invite widgets for selected organizations.
    # 1) For single organization
    #   * Multiple invite widgets for each email address of this organization
    #   * One invite widget with empty email
    # 2) For multiple organizations
    #   * One invite widget with empty email

    def setUp(self):
        # GIVEN monitoring with 2 organizations
        self.org1 = mommy.make(Organization, email='a@test.ru, b@test.ru')
        self.org2 = mommy.make(Organization, monitoring=self.org1.monitoring)

        # AND I am logged in as expertA
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.login('expertA', 'password')

        # AND I am on "organizations" page
        self.get(reverse('exmo2010:manage_orgs', args=[self.org1.monitoring.pk]))

    def test_multiple_orgs_group_action(self):
        # WHEN I tick first and second organizations checkbox
        self.find('#org_row_%s input.group_actions' % self.org1.pk).click()
        self.find('#org_row_%s input.group_actions' % self.org2.pk).click()

        # THEN "Create invite link" group-action button should become enabled
        self.assertEnabled('#group_actions input.create_inv_links')

        # WHEN i click "Create invite link" button
        self.find('#group_actions input.create_inv_links').click()

        # THEN invite links modal window should become visible
        self.assertVisible('#invite_links_window')

        email_inputs = self.findall('.invite_widgets input.email')
        displayed_emails = [i.get_attribute('value') for i in email_inputs if i.is_displayed()]

        # AND one empty email address should be displayed
        self.assertEqual(displayed_emails, [''])

        inv_inputs = self.findall('.invite_widgets input.invite_link')
        displayed_links = [inp.get_attribute('value') for inp in inv_inputs if inp.is_displayed()]

        # AND only one link should be displayed
        self.assertEqual(len(displayed_links), 1)

        generated_query = parse_qs(urlparse(displayed_links[0]).query)

        # AND displayed link query params should have only "code" parameter without "email"
        self.assertEqual(set(generated_query), {'code'})

        # AND displayed link "code" query parameter should include all selected organizations codes
        self.assertEqual(set(generated_query['code']), {self.org1.inv_code, self.org2.inv_code})

    def test_single_org_group_action(self):
        # WHEN I tick first organization checkbox
        self.find('#org_row_%s input.group_actions' % self.org1.pk).click()

        # THEN "Create invite link" group-action button should become enabled
        self.assertEnabled('#group_actions input.action')

        # WHEN i click "Create invite link" button
        self.find('#group_actions input.action').click()

        # THEN single org invite widgets should be displayed
        self._test_single_org_widgets(self.org1)

    def test_single_org_link_icon_click(self):
        # WHEN I click first organization link icon
        self.find('#org_row_%s a.org_invite_link' % self.org1.pk).click()

        # THEN single org invite widgets should be displayed
        self._test_single_org_widgets(self.org1)

    def _test_single_org_widgets(self, org):
        # THEN invite links modal window should become visible
        self.assertVisible('#invite_links_window')

        email_inputs = self.findall('.invite_widgets input.email')
        displayed_emails = [i.get_attribute('value') for i in email_inputs if i.is_displayed()]

        inv_inputs = self.findall('.invite_widgets input.invite_link')
        displayed_links = [inp.get_attribute('value') for inp in inv_inputs if inp.is_displayed()]

        # AND total number of displayed widgets should equal number of org email addresses + 1 (widget with empty email)
        expected_num_widgets = len(org.email.split(', ')) + 1
        self.assertEqual(len(displayed_emails), expected_num_widgets)
        self.assertEqual(len(displayed_links), expected_num_widgets)

        # AND each email address of organization should be displayed
        self.assertTrue(set(org.email.split(', ')).issubset(set(displayed_emails)))

        # AND one empty email address should be displayed
        self.assertTrue('' in set(displayed_emails))

        for link in displayed_links:
            query = parse_qs(urlparse(link).query)

            # AND every generated link should have "code" query parameter
            self.assertTrue("code" in query)

            # AND every "code" query parameter is equal to selected organization inv_code
            self.assertTrue(query["code"], org.inv_code)


@attr('selenium')
class OrganizationsVerifyJavasciptInviteLinksTestCase(BaseSeleniumTestCase):
    # exmo2010:manage_orgs

    # Invite links generated in javascript should be equal to server-generated.

    def setUp(self):
        # GIVEN organization
        self.org = mommy.make(Organization, email='a@test.ru, b@test.ru')

        # AND I am logged in as expertA
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.login('expertA', 'password')

        # AND server-side view that generates invite links
        self.sendmailview = SendMailView(request=self.requestfactory.get(''))

        # AND I am on "organizations" page
        self.get(reverse('exmo2010:manage_orgs', args=[self.org.monitoring.pk]))

    def test_single_org_link_icon_click(self):
        # WHEN I click first organization link icon
        self.find('#org_row_%s a.org_invite_link' % self.org.pk).click()

        # THEN invite links modal window should become visible
        self.assertVisible('#invite_links_window')

        # AND each widget should have generated link equal to the link generated by the server
        for widget in self.findall('.invite_widgets tr'):
            if widget.is_displayed():
                email = widget.find('input.email').get_attribute('value')
                javascript_generated_link = widget.find('input.invite_link').get_attribute('value')
                server_generated_link = self.sendmailview.replace_link('%link%', email, [self.org])
                self.assertEqual(server_generated_link, javascript_generated_link)
