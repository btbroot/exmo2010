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
from datetime import datetime
from itertools import product

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from model_mommy import mommy
from nose.plugins.attrib import attr
from nose_parameterized import parameterized
from selenium.webdriver.common.keys import Keys

from core.test_utils import BaseSeleniumTestCase
from custom_comments.models import CommentExmo
from exmo2010.models import User, Organization, Task, Parameter, Score, UserProfile, Claim, OrgUser
from exmo2010.models.monitoring import (
    Monitoring, MONITORING_RATE, MONITORING_RESULT, MONITORING_INTERACTION, MONITORING_FINALIZING, MONITORING_PUBLISHED)


@attr('selenium')
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
        kwargs = dict(accessible=True, complete=False, topical=False, hypertext=False, document=False, image=False)
        parameter = mommy.make(Parameter, monitoring=monitoring, npa=False, **kwargs)

        # AND score with found = 0
        score = mommy.make(Score, task=task, parameter=parameter, found=0)

        # AND i am logged in as expertB
        self.login('expertB', 'password')
        # AND i am on score page
        self.get(reverse('exmo2010:score', args=(score.pk,)))
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
            self.assertTrue(text.endswith(u'- → 3'))

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

            # AND third line should say that 'accessible' changed from - to 2
            text = self.find('#accessible_brick').get_attribute('value')
            self.assertTrue(text.endswith(u'- → 2'))

    def test_autoremove_autoscore_comments(self):
        # WHEN i set 'found' value to 1
        self.find('label[for="id_found_2"]').click()

        # AND i set 'accessible' value to 2
        self.find('label[for="id_accessible_2"]').click()

        with self.frame('iframe'):
            # THEN 3 comment lines should be added automatically
            self.assertEqual(len(self.findall('input.autoscore')), 3)

        # WHEN i set 'found' value back to 0
        self.find('label[for="id_found_1"]').click()

        with self.frame('iframe'):
            # THEN all comment lines should be removed automatically
            self.assertEqual(len(self.findall('input.autoscore')), 0)


@attr('selenium')
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
        self.get(reverse('exmo2010:score', args=(score.pk,)))
        # AND i clicked 'change score'
        self.assertVisible('a[href="#change_score"]')
        self.find('a[href="#change_score"]').click()

    def test_criteria_inputs_disable(self):
        # WHEN i just opened page ("found" value equals 0)
        # THEN "topical" criterion inputs should be hidden
        self.assertHidden('label[for="id_topical_2"]')

        # WHEN i set "found" criterion to "1"
        self.find('label[for="id_found_2"]').click()

        # THEN "topical" criterion inputs should become visible
        self.assertVisible('label[for="id_topical_2"]')


@attr('selenium')
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
        url = reverse('exmo2010:task_scores', args=(self.opened_task.pk,))
        # WHEN I am on score page for opened task
        self.get(url)
        # THEN rating place should not exist
        self.assertEqual(self.find('#rating_place'), None)

    def test_approved_task_rating_visible(self):
        url = reverse('exmo2010:task_scores', args=(self.approved_task.pk,))
        # WHEN I am on score page for approved task
        self.get(url)
        # THEN rating place should be visible
        self.assertVisible('#rating_place')


@attr('selenium')
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
        mommy.make(OrgUser, organization=org, userprofile=orguser.profile)
        # AND approved task assigned to expert B
        task = mommy.make(Task, organization=org, user=expertB, status=Task.TASK_APPROVED)

        # AND parameter with only 'found' and 'accessible' attribute
        kwargs = dict(accessible=True, complete=False, topical=False, hypertext=False, document=False, image=False)
        parameter = mommy.make(Parameter, monitoring=monitoring, npa=False, **kwargs)

        # AND score with found = 1 and accessible = 1
        self.score = mommy.make(Score, task=task, parameter=parameter, found=1, accessible=1)

    def test_orguser(self):
        # WHEN I login as organization representative
        self.login('orguser', 'password')

        # AND I get score page
        self.get(reverse('exmo2010:score', args=(self.score.pk,)))

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

    def test_expertb_reply(self):
        # WHEN I login as expertB
        self.login('expertB', 'password')

        # AND I get score page with 'reply' hash
        self.get('{}#reply'.format(reverse('exmo2010:score', args=(self.score.pk,))))

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

    def test_expertb_edit_score(self):
        # WHEN I login as expertB
        self.login('expertB', 'password')

        # AND I get score page
        self.get(reverse('exmo2010:score', args=(self.score.pk,)))

        # AND click to 'change_score' pseudo link
        self.find('a[href="#change_score"]').click()

        # THEN form with 'accessible' radio input should become visible
        self.assertVisible('label[for="id_accessible_2"]')

        # WHEN I set 'accessible' value to 2
        self.find('label[for="id_accessible_2"]').click()

        # AND fill recommendation field
        self.find('div.recommendations > textarea#id_recommendations').send_keys('new recommendation')

        # THEN submit button should be disabled
        self.assertDisabled('#submit_score_and_comment')

        with self.frame('.comment-form iframe'):
            self.assertVisible('#accessible_brick')
            # WHEN I type new line character in the comment area after autocomment brick
            self.find('body').send_keys(Keys.DOWN * 2 + '\n')

        # THEN submit button still should be disabled
        self.assertDisabled('#submit_score_and_comment')

        with self.frame('.comment-form iframe'):
            # WHEN I type something in the comment area
            self.find('body').send_keys('hi')

        # THEN submit button should turn enabled
        self.assertEnabled('#submit_score_and_comment')

        with self.frame('iframe'):
            # WHEN I erase all literal text symbols
            self.find('body').send_keys('\b\b')

        # THEN submit button should turn disabled
        self.assertDisabled('#submit_score_and_comment')


@attr('selenium')
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
            self.score_urls[status] = reverse('exmo2010:score', args=(score.pk,))

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


@attr('selenium')
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
            mommy.make(OrgUser, organization=org, userprofile=orguser.profile)

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
        self.get(reverse('exmo2010:score', args=(self.scores[status].pk,)))

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


@attr('selenium')
class AddClaimTestCase(BaseSeleniumTestCase):
    # On score page expertA should be able to add claim.

    statuses = (MONITORING_RATE, MONITORING_RESULT)

    def setUp(self):
        self.scores = {}

        # GIVEN I am logged in as expertA
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.login('expertA', 'password')

        # AND orguser comments for scores in monitorings for all relevant monitoring statuses
        for status in self.statuses:
            org = mommy.make(Organization, monitoring__status=status)
            task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)
            score = mommy.make(Score, task=task, parameter__monitoring=org.monitoring)
            self.scores[status] = score

    @parameterized.expand(zip(statuses))
    def test_add_claim(self, status):
        # WHEN I get score page
        self.get(reverse('exmo2010:score', args=(self.scores[status].pk,)))

        # THEN 'claims' tab handler should be visible
        self.assertVisible('a[href="#claims"]')

        # WHEN i click 'claims' tab handler
        self.find('a[href="#claims"]').click()

        # THEN claim form ckeditor iframe should become visible
        self.assertVisible('#add-claim iframe')

        # AND answer submit button should be disabled
        self.assertDisabled('#add-claim input[type="submit"]')

        with self.frame('#add-claim iframe'):
            # WHEN I type something in answer form
            self.find('body').send_keys('lol')

        # THEN submit button should become enabled
        self.assertEnabled('#add-claim input[type="submit"]')

        # WHEN I click submit
        self.find('#add-claim input[type="submit"]').click()

        # THEN page should reload, and claim should be displayed
        self.assertVisible('div.messages-content')

        # AND claim should be added in DB
        self.assertEqual(list(self.scores[status].claim_set.values_list('comment')), [('<p>lol</p>\r\n',)])


@attr('selenium')
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
        self.get(reverse('exmo2010:score', args=(self.scores[status].pk,)))

        # THEN 'claims' tab handler should be visible
        self.assertVisible('a[href="#claims"]')

        # WHEN i click 'claims' tab handler
        self.find('a[href="#claims"]').click()

        # THEN 'answer_form_toggle' link should become visible
        self.assertVisible('a.answer_form_toggle')

        # WHEN i click 'answer_form_toggle' link
        self.find('a.answer_form_toggle').click()

        # THEN answer submit button should be disabled
        self.assertDisabled('.answer_form input[type="submit"]')

        self.assertVisible('.answer_form iframe')
        with self.frame('.answer_form iframe'):
            # WHEN I type something in answer form
            self.find('body').send_keys('lol')

        # THEN submit button should become enabled
        self.assertEnabled('.answer_form input[type="submit"]')

        # WHEN I click submit
        self.find('.answer_form input[type="submit"]').click()

        # THEN page should reload, answer should be displayed under claim
        self.assertVisible('div.messages-answer')

        # AND claim answer should be added in DB
        self.assertEqual(list(self.scores[status].claim_set.values_list('answer')), [('<p>lol</p>\r\n',)])


@attr('selenium')
class ScoreRecommendationsShouldExistJsTestCase(BaseSeleniumTestCase):
    # If score is not maximum, recommendations submit button should be disabled if contents empty.
    # Exception cases, when recommendations MAY be omitted:
    #  * When monitoring has "no_interact" flag set to True.

    def setUp(self):
        self.scores = {}

        # GIVEN I am logged in as expertB
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        self.login('expertB', 'password')

        # AND organization with task in INTERACTION monitoring
        self.org = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION)
        task = mommy.make(Task, organization=self.org, user=expertB, status=Task.TASK_APPROVED)

        # AND parameter with one criterion (for ex. "topical")
        param_topical = mommy.make(
            Parameter,
            monitoring=self.org.monitoring,
            topical=True,
            image=False,
            complete=False,
            accessible=False,
            hypertext=False,
            document=False,
        )

        # AND score with found=0 (non-max)
        self.score_nonmax = mommy.make(Score, task=task, parameter__monitoring=self.org.monitoring, found=0)
        # AND score with all max criteria
        self.score_max = mommy.make(Score, task=task, parameter=param_topical, found=1, topical=3)

    def test_max_score(self):
        """
        Recommendations MAY be omitted when score is maximum.
        """

        # WHEN i get max score page
        self.get(reverse('exmo2010:score', args=(self.score_max.pk,)))

        # THEN 'edit_recommendations' button should be visible
        self.assertVisible('#edit_recommendations')

        # WHEN i click 'edit_recommendations'
        self.find('#edit_recommendations').click()

        # THEN 'submit' button should be enabled
        self.assertEnabled('#recommendations_form input[type="submit"]')

    def test_nonmax_score(self):
        """
        Recommendations SHOULD exist when score is evaluated to non-maximum.
        """

        # WHEN i get nonmax score page
        self.get(reverse('exmo2010:score', args=(self.score_nonmax.pk,)))

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

    def test_nonmax_no_interact(self):
        """
        Recommendations MAY be omitted when monitoring "no_interact" flag set to True.
        """

        # WHEN monitoring "no_interact" flag set to True
        Monitoring.objects.filter(pk=self.org.monitoring.pk).update(no_interact=True)

        # WHEN i get nonmax score page
        self.get(reverse('exmo2010:score', args=(self.score_nonmax.pk,)))

        # THEN 'edit_recommendations' button should be visible
        self.assertVisible('#edit_recommendations')

        # WHEN i click 'edit_recommendations'
        self.find('#edit_recommendations').click()

        # THEN 'submit' button should be enabled
        self.assertEnabled('#recommendations_form input[type="submit"]')


@attr('selenium')
class ToggleInitialScoresDisplayTestCase(BaseSeleniumTestCase):
    # exmo2010:score

    # On score page non-experts should be able to toggle initial scores visibility

    def setUp(self):
        # GIVEN PUBLISHED monitoring with organization
        monitoring_published = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        org = mommy.make(Organization, monitoring=monitoring_published)
        # AND user without any permissions
        User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.is_organization = True
        mommy.make(OrgUser, organization=org, userprofile=orguser.profile)
        # AND approved task
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
        self.get(reverse('exmo2010:score', args=(self.score1.pk,)))
        # THEN initial scores should be hidden
        self.assertHidden('.score-interim')

        # WHEN I click 'show_interim_score'
        self.find('a[href="#show_interim_score"]').click()
        # THEN initial scores should be visible
        self.assertVisible('.score-interim')

        # WHEN I click 'show_interim_score' again
        self.find('a[href="#show_interim_score"]').click()
        # THEN initial scores should be hidden
        self.assertHidden('.score-interim')


@attr('selenium')
class ToggleHiddenCommentsDisplayTestCase(BaseSeleniumTestCase):
    # exmo2010:recommendations

    # On recommendations page organizations representatives should be able to toggle hidden comments visibility.
    # For finished or nonrelevant scores all comments should be initially hidden.
    # For other scores, all comments except the last 2 should be initially hidden.

    def setUp(self):
        content_type = ContentType.objects.get_for_model(Score)

        # GIVEN organization in PUBLISHED monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_PUBLISHED)
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.is_organization = True
        mommy.make(OrgUser, organization=org, userprofile=orguser.profile)
        # AND approved task
        self.task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)
        # AND 100% score
        param = mommy.make(Parameter, monitoring=org.monitoring, weight=1)
        self.score_100 = mommy.make(Score, task=self.task, parameter=param, found=1)
        # AND 0% score
        param = mommy.make(Parameter, monitoring=org.monitoring, weight=1)
        self.score_0 = mommy.make(Score, task=self.task, parameter=param, found=0)
        # AND nonrelevant score
        param = mommy.make(Parameter, monitoring=org.monitoring, weight=1)
        org.parameter_set = [param]  # non-relevant param
        self.score_nonerelevant = mommy.make(Score, task=self.task, parameter=param, found=0)

        def comment(score, dt):
            return mommy.make(
                CommentExmo, submit_date=datetime(2005, 1, 1 + dt), object_pk=score.pk,
                content_type=content_type, site__pk=settings.SITE_ID, user=orguser, comment='123')

        # AND 3 comments for each score
        self.score_100.comments = [comment(self.score_100, n) for n in range(3)]
        self.score_0.comments = [comment(self.score_0, n) for n in range(3)]
        self.score_nonerelevant.comments = [comment(self.score_nonerelevant, n) for n in range(3)]

    def test_score_comments_toggle(self):
        # WHEN I login as representative
        self.login('orguser', 'password')

        # AND I get recommendations page
        self.get(reverse('exmo2010:recommendations', args=(self.task.pk,)))

        # THEN first comment of unfinished score should be hidden
        self.assertHidden('#comment_%s' % self.score_0.comments[0].pk)

        # AND last 2 comments of unfinished score should be visible
        self.assertVisible('#comment_%s' % self.score_0.comments[1].pk)
        self.assertVisible('#comment_%s' % self.score_0.comments[2].pk)

        # AND all finished score comments should be hidden
        for comment in self.score_100.comments:
            self.assertHidden('#comment_%s' % comment.pk)

        # AND all nonrelevant score comments should be hidden
        for comment in self.score_nonerelevant.comments:
            self.assertHidden('#comment_%s' % comment.pk)

        # WHEN I click 'show all comments' for each score
        self.find('#param%s div.comment-toggle.show' % self.score_0.parameter.pk).click()
        self.find('#param%s div.comment-toggle.show' % self.score_100.parameter.pk).click()
        self.find('#param%s div.comment-toggle.show' % self.score_nonerelevant.parameter.pk).click()

        # THEN all scores comments should become visible
        for comment in self.score_0.comments:
            self.assertVisible('#comment_%s' % comment.pk)
        for comment in self.score_100.comments:
            self.assertVisible('#comment_%s' % comment.pk)
        for comment in self.score_nonerelevant.comments:
            self.assertVisible('#comment_%s' % comment.pk)

        # WHEN I click 'hide comments' for each score
        self.find('#param%s div.comment-toggle.hide' % self.score_0.parameter.pk).click()
        self.find('#param%s div.comment-toggle.hide' % self.score_100.parameter.pk).click()
        self.find('#param%s div.comment-toggle.hide' % self.score_nonerelevant.parameter.pk).click()

        # THEN first comment of unfinished score should be hidden
        self.assertHidden('#comment_%s' % self.score_0.comments[0].pk)

        # AND last 2 comments of unfinished score should be visible
        self.assertVisible('#comment_%s' % self.score_0.comments[1].pk)
        self.assertVisible('#comment_%s' % self.score_0.comments[2].pk)

        # AND all finished score comments should be hidden
        for comment in self.score_100.comments:
            self.assertHidden('#comment_%s' % comment.pk)

        # AND all nonrelevant score comments should be hidden
        for comment in self.score_nonerelevant.comments:
            self.assertHidden('#comment_%s' % comment.pk)


@attr('selenium')
class ScoreEditInteractionJsTestCase(BaseSeleniumTestCase):
    # exmo2010:score

    # BUG 2194: Comments are not saved in "score change" mode.

    # ExpertA and expertB assigned to task should be able to edit score in INTERACTION monitoring.
    # And comment should be added

    def setUp(self):
        # GIVEN expert A account
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND expert B account
        expertB = User.objects.create_user('expertB', 'usr@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND organization with task in INTERACTION monitoring
        self.org = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION)
        task = mommy.make(Task, organization=self.org, user=expertB)
        # AND parameter with only "found" criterion
        criteria = {crit: False for crit in Parameter.OPTIONAL_CRITERIA}
        param = mommy.make(Parameter, monitoring=self.org.monitoring, **criteria)
        # AND score with found = 0
        score = mommy.make(Score, task=task, parameter=param, found=0)

        self.url = reverse('exmo2010:score', args=(score.pk,))

    @parameterized.expand([
        ('expertA',),
        ('expertB',),
    ])
    def test_edit_score_and_post_comment(self, username):
        # WHEN I log in as expert
        self.login(username, 'password')
        # AND get score page
        self.get(self.url)
        # THEN comments should not exist
        self.assertEquals(self.find('.table-messages-parameter'), None)

        # WHEN I click "change score"
        self.find('a[href="#change_score"]').click()
        # AND post comment "Comment"
        with self.frame('iframe'):
            # WHEN I type new line character in the comment area
            self.find('body').send_keys('Comment')
        # AND change found score to 1
        self.find('label[for="id_found_2"]').click()
        # AND submit all changes
        self.find('#submit_score_and_comment').click()
        # THEN comments should exist
        self.assertVisible('.table-messages-parameter tr#c1')
        # AND visible comment text and posted comment text should be equal
        self.assertEquals(self.find('tr#c1 div.messages-content div p:nth-child(2)').text, 'Comment')


@attr('selenium')
class CkeditorInstancesLimitTestCase(BaseSeleniumTestCase):
    # exmo2010:recommendations

    # BUG 2377: CKEditor script raises "too much recursion" in Firefox on recommendations page

    # Firefox only. When there are too many recommendations (about 100+), CKEditor instances will fail to
    # initialize, so the user is unable to leave comments from this page. Browser log indicates javascript exception:
    # too much recursion     ckeditor.js:91:103

    def setUp(self):
        # GIVEN organization in INTERACTION monitoring
        org = mommy.make(Organization, monitoring__status=MONITORING_INTERACTION)

        # AND organization representative
        orguser = User.objects.create_user('orguser', 'orguser@svobodainfo.org', 'password')
        orguser.profile.is_organization = True
        mommy.make(OrgUser, organization=org, userprofile=orguser.profile)
        # AND approved task
        self.task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)
        # AND 150 0% scores with recommendations
        for p in range(150):
            param = mommy.make(Parameter, code=p, monitoring=org.monitoring, weight=1)
            mommy.make(Score, task=self.task, parameter=param, found=0, recommendations='lol')

    def test_recursion(self):
        # WHEN I login as org representative
        self.login('orguser', 'password')

        # AND I get recommendations page
        self.get(reverse('exmo2010:recommendations', args=(self.task.pk,)))

        # THEN browser severe errors log should not contain "too much recursion"
        messages = self.webdrv.get_log('browser')
        severe_messages = [msg['message'] for msg in messages if msg['level'] == u'SEVERE']
        if 'too much recursion' in severe_messages:
            raise AssertionError('CKEditor script raises "too much recursion"')
