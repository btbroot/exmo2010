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
from datetime import datetime
from itertools import product

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from model_mommy import mommy
from nose_parameterized import parameterized

from core.test_utils import BaseSeleniumTestCase
from custom_comments.models import CommentExmo
from exmo2010.models import User, Organization, Task, Parameter, Score, UserProfile, Claim
from exmo2010.models.monitoring import (
    Monitoring, MONITORING_RATE, MONITORING_RESULT, MONITORING_INTERACTION, MONITORING_FINALIZING, MONITORING_PUBLISHED)


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
        self.find('label[for="id_found_2"]').click()
        self.find('label[for="id_accessible_3"]').click()

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
        self.find('label[for="id_found_2"]').click()

        # AND i set 'accessible' value to 2 (NOT maximum)
        self.find('label[for="id_accessible_2"]').click()

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
        self.find('label[for="id_found_2"]').click()

        with self.frame('iframe'):
            # THEN 2 comment lines should be added automatically
            self.assertEqual(len(self.findall('input.autoscore')), 2)

        # WHEN i set 'found' value back to 0
        self.find('label[for="id_found_1').click()

        with self.frame('iframe'):
            # THEN all comment lines should be removed automatically
            self.assertEqual(len(self.findall('input.autoscore')), 0)

    def test_disable_submit(self):
        # WHEN nothing is typed in comment area explicitly
        # AND i set 'found' value to 1
        self.find('label[for="id_found_2"]').click()

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


class CriteriaValuesDependencyTestCase(BaseSeleniumTestCase):
    ''' On score page if "found" criterion value is not "1", then other criteria inputs should be hidden '''

    def setUp(self):
        # GIVEN organization with task in INTERACTION monitoring
        org = mommy.make(Organization, name='org', monitoring__status=MONITORING_INTERACTION)
        task = mommy.make(Task, organization=org, status=Task.TASK_OPEN)

        # AND score with "found" ctriterion set to 0
        score = mommy.make(Score, task=task, parameter__monitoring=org.monitoring, found=0)

        # AND i am logged in as expertA
        expertA = User.objects.create_user('expertA', 'expertB@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.login('expertA', 'password')
        # AND i am on score page
        self.get(reverse('exmo2010:score_view', args=(score.pk,)))
        # AND i clicked 'change score'
        self.assertVisible('a[href="#change_score"]')
        self.find('a[href="#change_score"]').click()

    def test_criteria_inputs_disable(self):
        # WHEN i just opened page ("found" value equals 0)
        # THEN "topical" creiterion inputs should be hidden
        self.assertHidden('label[for="id_topical_2"]')

        # WHEN i set "found" criterion to "1"
        self.find('label[for="id_found_2"]').click()

        # THEN "topical" creiterion inputs should become visible
        self.assertVisible('label[for="id_topical_2"]')


class TaskAjaxRatingVisibilityTestCase(BaseSeleniumTestCase):
    # Scenario: on task page rating place SHOULD be visible and requested by ajax only if task is approved

    def setUp(self):
        # GIVEN expert B account
        self.expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        self.expertB.profile.is_expertB = True
        # AND INTERACTION monitoring with two organizations
        monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        organization_1 = mommy.make(Organization, monitoring=monitoring, name='org1')
        organization_2 = mommy.make(Organization, monitoring=monitoring, name='org2')
        # AND one opened task
        self.opened_task = mommy.make(
            Task,
            organization=organization_1,
            user=self.expertB,
            status=Task.TASK_OPEN,
        )
        # AND one approved task
        self.approved_task = mommy.make(
            Task,
            organization=organization_2,
            user=self.expertB,
            status=Task.TASK_APPROVED,
        )
        # AND parameter with positive weight
        parameter = mommy.make(Parameter, monitoring=monitoring, weight=1)
        # AND score with zero initial values for parameter attributes
        mommy.make(Score, task=self.approved_task, parameter=parameter, found=0)

        # AND I am logged in as expert A
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.login('expertA', 'password')

    def test_opened_task_rating_hidden(self):
        url = reverse('exmo2010:score_list_by_task', args=(self.opened_task.pk,))
        # WHEN I am on score page for opened task
        self.get(url)
        # THEN rating place should be hidden
        self.assertHidden('#place_all')

    def test_approved_task_rating_visible(self):
        url = reverse('exmo2010:score_list_by_task', args=(self.approved_task.pk,))
        # WHEN I am on score page for approved task
        self.get(url)
        # THEN rating place should be visible
        self.assertVisible('#place_all')


class DisableEmptyCommentSubmitTestCase(BaseSeleniumTestCase):
    # On score page comment submit button should be disabled if input text is empty

    def setUp(self):
        # GIVEN INTERACTION monitoring with organization
        monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        org = mommy.make(Organization, monitoring=monitoring)
        # AND expert B account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND organization representative account
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.is_organization = True
        orguser.profile.organization = [org]
        # AND approved task assigned to expert B
        task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_APPROVED)
        # AND parameter
        parameter = mommy.make(Parameter, monitoring=monitoring)
        # AND score with zero initial values for parameter attributes
        self.score = mommy.make(Score, task=task, parameter=parameter)

    def test_orguser(self):
        # WHEN I login as organization representative
        self.login('orguser', 'password')

        # AND I get score page
        self.get(reverse('exmo2010:score_view', args=(self.score.pk,)))

        # THEN submit button should be disabled
        self.assertDisabled('#submit_comment')

        with self.frame('iframe'):
            # WHEN I type new line character in the comment area
            self.find('body').send_keys('\n')
        # THEN submit button still should be disabled
        self.assertDisabled('#submit_comment')

        with self.frame('iframe'):
            # WHEN I type something in the comment area
            self.find('body').send_keys('hi')
        # THEN submit button should turn enabled
        self.assertEnabled('#submit_comment')

        with self.frame('iframe'):
            # WHEN I erase all literal text symbols
            self.find('body').send_keys('\b\b')
        # THEN submit button should turn disabled
        self.assertDisabled('#submit_comment')

    def test_expertb(self):
        # WHEN I login as expertB
        self.login('expertB', 'password')

        # AND I get score page with 'reply' hash
        self.get('{}#reply'.format(reverse('exmo2010:score_view', args=(self.score.pk,))))

        # THEN submit button should be disabled
        self.assertDisabled('#submit_comment')

        with self.frame('iframe'):
            # WHEN I type new line character in the comment area
            self.find('body').send_keys('\n')
        # THEN submit button still should be disabled
        self.assertDisabled('#submit_comment')

        with self.frame('iframe'):
            # WHEN I type something in the comment area
            self.find('body').send_keys('hi')
        # THEN submit button should turn enabled
        self.assertEnabled('#submit_comment')

        with self.frame('iframe'):
            # WHEN I erase all literal text symbols
            self.find('body').send_keys('\b\b')
        # THEN submit button should turn disabled
        self.assertDisabled('#submit_comment')


class ScoreClaimTabsClickTestCase(BaseSeleniumTestCase):
    # On score page clicking on Claim\Clarification tabs should display tab content.

    statuses = (MONITORING_RATE, MONITORING_RESULT, MONITORING_INTERACTION, MONITORING_FINALIZING)

    def setUp(self):
        self.score_urls = {}

        # GIVEN expertA and expertB
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND scores in monitorings for all relevant monitoring statuses
        for status in self.statuses:
            org = mommy.make(Organization, monitoring__status=status)
            task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_OPEN)
            score = mommy.make(Score, task=task, parameter__monitoring=org.monitoring)
            self.score_urls[status] = reverse('exmo2010:score_view', args=(score.pk,))

    @parameterized.expand(product(['expertA', 'expertB'], statuses))
    def test_claims_tab_click(self, username, status):
        # WHEN I login
        self.login(username, 'password')

        # AND I get score page
        self.get(self.score_urls[status])

        # THEN tab contents should be hidden
        self.assertHidden('.tab-content-claims')
        self.assertHidden('.tab-content-clarifications')

        # WHEN i click 'claims' tab
        self.find('a[href="#claims"]').click()

        # THEN claims tab contents should become visible
        self.assertVisible('.tab-content-claims')
        self.assertHidden('.tab-content-clarifications')

        # WHEN i click 'clarifications' tab
        self.find('a[href="#clarifications"]').click()

        # THEN clarifications tab contents should become visible
        self.assertHidden('.tab-content-claims')
        self.assertVisible('.tab-content-clarifications')


class ScoreToggleCommentTestCase(BaseSeleniumTestCase):
    # On score page clicking "toggle comment" should change comment status.

    statuses = (MONITORING_INTERACTION, MONITORING_FINALIZING, MONITORING_PUBLISHED)

    def setUp(self):
        self.scores = {}
        content_type = ContentType.objects.get_for_model(Score)

        # GIVEN  I am logged in as expertA
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.login('expertA', 'password')

        # AND orguser comments for scores in monitorings for all relevant monitoring statuses
        for status in self.statuses:
            org = mommy.make(Organization, monitoring__status=status)
            task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)
            score = mommy.make(Score, task=task, parameter__monitoring=org.monitoring)

            orguser = User.objects.create_user('orguser %d' % status, 'org@svobodainfo.org', 'password')
            orguser.groups.add(Group.objects.get(name=UserProfile.organization_group))
            orguser.profile.organization = [org]

            mommy.make(
                CommentExmo,
                object_pk=score.pk,
                content_type=content_type,
                site__pk=settings.SITE_ID,
                user=orguser,
                status=CommentExmo.OPEN,
                submit_date=datetime.now(),
                comment='123')

            self.scores[status] = score

    @parameterized.expand(zip(statuses))
    def test_toggle(self, status):
        comments = CommentExmo.objects.filter(object_pk=self.scores[status].pk)

        # WHEN I get score page
        self.get(reverse('exmo2010:score_view', args=(self.scores[status].pk,)))

        # THEN toggle-comment buton should be visible
        self.assertVisible('.toggle-comment-container a')
        # AND comment with class "answer-later" should be visible
        self.assertVisible('table.table-messages-parameter td.answer-later')

        # WHEN i click 'toggle-comment'
        self.find('.toggle-comment-container a').click()

        # THEN comment with class "toggled" should become visible
        td = 'table.table-messages-parameter td.toggled'
        self.assertVisible(td)
        # AND old comment class should be removed (only "toggled" class left)
        self.assertEqual(self.find(td).get_attribute('class'), 'toggled')
        # AND comment should change status in DB to "ANSWERED"
        self.assertEqual(list(comments.values_list('status')), [(CommentExmo.NOT_ANSWERED,)])

        # WHEN i click 'claims' tab
        self.find('.toggle-comment-container a').click()

        # THEN comment with class "answer-later" should become visible
        self.assertVisible('table.table-messages-parameter td.answer-later')
        # AND comment should change status in DB to "OPEN"
        self.assertEqual(list(comments.values_list('status')), [(CommentExmo.OPEN,)])


class AnswerClaimTestCase(BaseSeleniumTestCase):
    # On score page expertB should be able to add claim answer.

    statuses = (MONITORING_RATE, MONITORING_INTERACTION, MONITORING_FINALIZING)

    def setUp(self):
        self.scores = {}

        # GIVEN expertA and expertB
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True

        # AND orguser comments for scores in monitorings for all relevant monitoring statuses
        for status in self.statuses:
            org = mommy.make(Organization, monitoring__status=status)
            task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_APPROVED)
            score = mommy.make(Score, task=task, parameter__monitoring=org.monitoring)
            mommy.make(Claim, creator=expertA, score=score, comment='123')
            self.scores[status] = score

        # AND  I am logged in as expertB
        self.login('expertB', 'password')

    @parameterized.expand(zip(statuses))
    def test_answer_claim(self, status):
        # WHEN I get score page
        self.get(reverse('exmo2010:score_view', args=(self.scores[status].pk,)))

        # THEN 'claims' tab handler should be visible
        self.assertVisible('a[href="#claims"]')

        # WHEN i click 'claims' tab handler
        self.find('a[href="#claims"]').click()

        # THEN 'answer-claim' link should become visible
        self.assertVisible('a.answer-claim')

        # WHEN i click 'answer-claim' link
        self.find('a.answer-claim').click()

        # THEN comment with class "answer-later" should be disabled
        self.assertDisabled('#add-claim input[type="submit"]')

        with self.frame('iframe'):
            # WHEN I type something in answer form
            self.find('body').send_keys('lol')

        # THEN submit button should become enabled
        self.assertEnabled('#add-claim input[type="submit"]')

        # WHEN I click submit
        self.find('#add-claim input[type="submit"]').click()

        # THEN page should reload, submit button should become hidden
        self.assertHidden('#add-claim input[type="submit"]')

        # AND claim answer should be added in DB
        self.assertEqual(list(self.scores[status].claim_set.values_list('answer')), [('lol',)])


class DisableNonMaxScoreEmptyRecommendationsSubmit(BaseSeleniumTestCase):
    # If score is not maximum, recommendations submit button should be disabled if contents empty.

    def setUp(self):
        self.scores = {}

        # GIVEN I am logged in as expertB
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        self.login('expertB', 'password')

        # AND organization with task in INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION)
        task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_APPROVED)

        # AND parameter with one ctriteria (for ex. "topical")
        param_topical = mommy.make(
            Parameter,
            monitoring=org.monitoring,
            topical=True,
            image=False,
            complete=False,
            accessible=False,
            hypertext=False,
            document=False,
        )

        # AND score with found=0 (non-max)
        self.score_nonmax = mommy.make(Score, task=task, parameter__monitoring=org.monitoring, found=0)
        # AND score with all max criteria
        self.score_max = mommy.make(Score, task=task, parameter=param_topical, found=1, topical=3)

    def test_nonmax_score(self):
        # WHEN i get nonmax score page
        self.get(reverse('exmo2010:score_view', args=(self.score_nonmax.pk,)))

        # THEN 'edit_recommendations' button should be visible
        self.assertVisible('#edit_recommendations')

        # WHEN i click 'edit_recommendations'
        self.find('#edit_recommendations').click()

        # THEN 'submit' button should be disabled
        self.assertDisabled('#recommendations_form input[type="submit"]')

        # WHEN i type recommendation text
        self.find('#recommendations_form textarea').send_keys('hi')

        # THEN 'submit' button should become enabled
        self.assertEnabled('#recommendations_form input[type="submit"]')

    def test_max_score(self):
        # WHEN i get max score page
        self.get(reverse('exmo2010:score_view', args=(self.score_max.pk,)))

        # THEN 'edit_recommendations' button should be visible
        self.assertVisible('#edit_recommendations')

        # WHEN i click 'edit_recommendations'
        self.find('#edit_recommendations').click()

        # THEN 'submit' button should be enabled
        self.assertEnabled('#recommendations_form input[type="submit"]')


class ToggleInitialScoresDisplayTestCase(BaseSeleniumTestCase):
    # On score page non-experts SHOULD be able to toggle initial scores visibility

    def setUp(self):
        # GIVEN PUBLISHED monitoring with organization
        monitoring_published = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        org = mommy.make(Organization, monitoring=monitoring_published)
        # AND user without any permissions
        User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.is_organization = True
        orguser.profile.organization = [org]
        # AND approved task assigned to expert B
        task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)
        # AND parameter
        parameter = mommy.make(Parameter, monitoring=monitoring_published, weight=1)
        # AND scores with two revisions
        self.score1 = mommy.make(Score, task=task, parameter=parameter, revision=0, found=1)
        self.score2 = mommy.make(Score, task=task, parameter=parameter, revision=1, found=0)

    @parameterized.expand([
        ('orguser',),
        ('user',),
        ('anonymous',)
    ])
    def test_non_experts(self, user):
        # WHEN I login as non expert user
        if user != 'anonymous':
            self.login(user, 'password')
        # AND I get score page
        self.get(reverse('exmo2010:score_view', args=(self.score1.pk,)))
        # THEN initial scores should be hidden
        self.assertHidden('.score_rev1')

        # WHEN I click 'show_score_rev1'
        self.find('a[href="#show_score_rev1"]').click()
        # THEN initial scores should be visible
        self.assertVisible('.score_rev1')

        # WHEN I click 'show_score_rev1'
        self.find('a[href="#show_score_rev1"]').click()
        # THEN initial scores should be hidden
        self.assertHidden('.score_rev1')
