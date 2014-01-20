# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
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
from django.core.urlresolvers import reverse
from model_mommy import mommy

from core.test_utils import BaseSeleniumTestCase
from exmo2010.models import User, Monitoring, Organization, Task, Parameter, Score, MONITORING_INTERACTION


class AutoScoreCommentTestCase(BaseSeleniumTestCase):
    ''' Tests automatic comments insertion when editing scores on score page '''

    def setUp(self):
        # GIVEN expertB account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND INTERACTION monitoring with organization, and task
        monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        organization = mommy.make(Organization, monitoring=monitoring)
        task = mommy.make(
            Task,
            organization=organization,
            user=expertB,
            status=Task.TASK_APPROVED,
        )

        # AND parameter with only 'accessible' attribute
        parameter = mommy.make(
            Parameter,
            monitoring=monitoring,
            complete = False,
            accessible = True,
            topical = False,
            hypertext = False,
            document = False,
            image = False,
            npa = False
        )

        # AND score with zero initial values for parameter attributes
        score = mommy.make(Score, task=task, parameter=parameter, found=0, accessible=0)

        # AND i am logged in as expertB
        self.login('expertB', 'password')
        # AND i am on score page
        self.get(reverse('exmo2010:score_view', args=(score.pk,)))
        # AND i opened change score tab
        self.find('a[href="#change_score"]').click()

    def test_all_maximum_scores(self):
        # WHEN i set all values to (maximum)
        self.find('#id_found_2').click()
        self.find('#id_accessible_3').click()

        with self.frame('iframe'):
            # THEN 3 comment lines should be added automatically
            self.assertEqual(len(self.findall('input.autoscore')), 3)

            # AND intro line should say that value changed to maximum (have 'max' class)
            cls = self.find('#autoscore-intro').get_attribute('class')
            self.assertTrue('max' in cls)

            # AND all other lines should say that values changed
            text = self.find('#found_brick').get_attribute('value')
            self.assertTrue(text.endswith(u'0 → 1'))
            text = self.find('#accessible_brick').get_attribute('value')
            self.assertTrue(text.endswith(u'0 → 3'))

    def test_two_scores(self):
        # WHEN i set 'found' value to 1 (maximum)
        self.find('#id_found_2').click()

        # AND i set 'accessible' value to 2 (NOT maximum)
        self.find('#id_accessible_2').click()

        with self.frame('iframe'):
            # THEN 3 comment lines should be added automatically
            self.assertEqual(len(self.findall('input.autoscore')), 3)

            # AND intro line should say that value changed, not to maximum (no 'max' class)
            cls = self.find('#autoscore-intro').get_attribute('class')
            self.assertFalse('max' in cls)

            # AND second line should say that 'found' changed from 0 to 1
            text = self.find('#found_brick').get_attribute('value')
            self.assertTrue(text.endswith(u'0 → 1'))

            # AND third line should say that 'accessible' changed from 0 to 2
            text = self.find('#accessible_brick').get_attribute('value')
            self.assertTrue(text.endswith(u'0 → 2'))

    def test_autoremove_autoscore_comments(self):
        # WHEN i set 'found' value to 1
        self.find('#id_found_2').click()

        with self.frame('iframe'):
            # THEN 2 comment lines should be added automatically
            self.assertEqual(len(self.findall('input.autoscore')), 2)

        # WHEN i set 'found' value back to 0
        self.find('#id_found_1').click()

        with self.frame('iframe'):
            # THEN all comment lines should be removed automatically
            self.assertEqual(len(self.findall('input.autoscore')), 0)

    def test_disable_submit(self):
        # WHEN nothing is typed in comment area explicitly
        # AND i set 'found' value to 1
        self.find('#id_found_2').click()

        # THEN submit button should stay disabled
        self.assertDisabled('#submit_score_and_comment')

        with self.frame('iframe'):
            # WHEN i type something in the comment area
            self.find('body').send_keys('hi')

        # THEN submit button should be enabled
        self.assertEnabled('#submit_score_and_comment')

        with self.frame('iframe'):
            # WHEN i erase text in the comment area
            self.find('body').send_keys('\b\b')

        # THEN submit button should turn disabled
        self.assertDisabled('#submit_score_and_comment')


class PrintfullPageTestCase(BaseSeleniumTestCase):
    # Scenario: checking comments fields

    def setUp(self):
        # GIVEN expertB account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND monitoring with organization, parameter, and task
        monitoring = mommy.make(Monitoring)
        organization = mommy.make(Organization, monitoring=monitoring)
        parameter = mommy.make(Parameter, monitoring=monitoring)
        task = mommy.make(
            Task,
            organization=organization,
            user=expertB,
        )
        # AND score with 'found' equals 1 and 2 comments
        self.score = mommy.make(
            Score,
            task=task,
            parameter=parameter,
            found=1,
            foundComment='found comment',
            imageComment='image comment',
        )
        # AND I am logged in as expertB
        self.login('expertB', 'password')
        # AND I am on score printfull page
        self.get(reverse('exmo2010:score_list_by_task', args=[task.pk]) + 'printfull')

    def test_comments_fields_existing(self):
        # WHEN I try to get comments texts of 'found' and 'image' fields
        found_comment = self.find('tbody > tr:nth-child(2) > td:nth-child(2) > p').text
        image_comment = self.find('tbody > tr:nth-child(3) > td:nth-child(2) > p').text
        # THEN texts should exist
        self.assertEqual(found_comment, self.score.foundComment)
        self.assertEqual(image_comment, self.score.imageComment)


class CriteriaValuesDependencyTestCase(BaseSeleniumTestCase):
    ''' On score page if "found" criterion value is not "1", then other criteria inputs should be disabled '''

    def setUp(self):
        # GIVEN expertA account
        expertA = User.objects.create_user('expertA', 'expertB@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND expertB account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND organization with task in INTERACTION monitoring
        org = mommy.make(Organization, name='org', monitoring__status=MONITORING_INTERACTION)
        task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_OPEN)

        # AND parameter with one ctriteria (for ex. "topical")
        parameter = mommy.make(
            Parameter,
            monitoring=org.monitoring,
            topical=True,
            image=False,
            complete=False,
            accessible=False,
            hypertext=False,
            document=False,
        )
        # AND score with "found" ctriterion set to 0
        score = mommy.make(Score, task=task, parameter=parameter, found=0)

        # AND i am logged in as expertA
        self.login('expertA', 'password')
        # AND i am on score page
        self.get(reverse('exmo2010:score_view', args=(score.pk,)))
        # AND i clicked 'change score'
        self.assertVisible('a[href="#change_score"]')
        self.find('a[href="#change_score"]').click()

    def assert_topical_criterion_enabled(self, is_enabled):
        # "Topical" criterion comment textarea
        self.assertEqual(self.find('#id_topicalComment').is_enabled(), is_enabled)

        # "Topical" criterion value radio inputs
        for radio in self.findall('input[name="topical"]'):
            self.assertEqual(radio.is_enabled(), is_enabled)

        # BUG 1856: Claim and clarification textareas should always be enabled
        self.assertEnabled('#id_clarification-comment')
        self.assertEnabled('#id_claim-comment')

    def test_criteria_inputs_disable(self):
        # WHEN i just opened page ("found" value equals 0)
        # THEN "topical" creiterion inputs should be disabled
        self.assert_topical_criterion_enabled(False)

        # WHEN i set "found" criterion to "1"
        self.find('#id_found_2').click()

        # THEN "topical" creiterion inputs should get enabled
        self.assert_topical_criterion_enabled(True)
