# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
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
from datetime import datetime, timedelta

from django.contrib.auth.models import AnonymousUser, User, Group
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.test import TestCase
from mock import Mock, patch
from model_mommy import mommy
from nose_parameterized import parameterized

from core.test_utils import OptimizedTestCase
from custom_comments.models import CommentExmo
from custom_comments.utils import comment_report
from exmo2010.celery_tasks import send_digest
from exmo2010.models.monitoring import Monitoring, MONITORING_PUBLISHED, MONITORING_INTERACTION, MONITORING_STATUS
from exmo2010.models import Organization, Parameter, Score, Task, UserProfile
from scores.views import post_score_comment


class CommentReportTestCase(TestCase):
    # Test comment report generation

    def setUp(self):
        # GIVEN monitoring
        self.monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED, time_to_answer=3)
        # AND 3 organizations
        self.org1 = mommy.make(Organization, name='org1', monitoring=self.monitoring)
        self.org2 = mommy.make(Organization, name='org2', monitoring=self.monitoring)
        self.org_orphan = mommy.make(Organization, monitoring=self.monitoring)
        # AND 2 organization representatives for org1
        org1user1 = mommy.make(User)
        org1user1.profile.organization.add(self.org1)
        org1user2 = mommy.make(User)
        org1user2.profile.organization.add(self.org1)
        # AND 1 organization representative for org2
        org2user1 = mommy.make(User)
        org2user1.profile.organization.add(self.org2)
        # AND expertA
        expertA = mommy.make(User)
        expertA.profile.is_expertA = True
        # AND expertB
        expertB = mommy.make(User, username='expertB')
        expertB.profile.is_expertB = True

        # AND approved task for org1 and org2
        task1 = mommy.make(Task, status=Task.TASK_APPROVED, organization=self.org1, user=expertB)
        task2 = mommy.make(Task, status=Task.TASK_APPROVED, organization=self.org2, user=expertB)
        # AND scores for tasks
        score1 = mommy.make(Score, task=task1)
        score2 = mommy.make(Score, task=task2)

        init_date = datetime.today() - timedelta(days=30)
        late = init_date + timedelta(days=25)

        # AND comment by org1user1 that was answered in time
        mommy.make(
            CommentExmo, object_pk=score1.pk, user=org1user1, submit_date=init_date,
            status=CommentExmo.ANSWERED, answered_date=init_date)

        # AND 1 comment by org2user1 that was not answered
        mommy.make(
            CommentExmo, object_pk=score2.pk, user=org2user1, submit_date=init_date,
            status=CommentExmo.OPEN)
        # AND 1 comment by org2user1 that was answered late
        mommy.make(
            CommentExmo, object_pk=score2.pk, user=org2user1, submit_date=init_date,
            status=CommentExmo.ANSWERED, answered_date=late)

        # AND 1 comment by expertB for org1
        mommy.make(CommentExmo, object_pk=score1.pk, user=expertB)
        # AND 1 comment by expertB for org2
        mommy.make(CommentExmo, object_pk=score2.pk, user=expertB)

    def test_count_of_organizations_with_representatives(self):
        report = comment_report(self.monitoring)
        self.assertEqual(report['num_orgs_with_user'], 2)

        active_orgs = set(tuple(x.items()) for x in report['active_orgs'])
        expected = [
            (('num_comments', 1), ('name', u'org1'), ('expert', u'expertB')),
            (('num_comments', 2), ('name', u'org2'), ('expert', u'expertB'))]
        self.assertEqual(active_orgs, set(expected))

        active_experts = set((e.username, e.num_comments) for e in report['active_experts'])
        self.assertEqual(active_experts, set([('expertB', 2)]))

        self.assertEqual(report['num_answered'], 2)
        self.assertEqual(report['num_answered_late'], 1)


class OpenCommentsAnswerTimeUrgencyTestCase(TestCase):
    # Unanswered comments should be divided in expired, urgent and non-urgent, depending on
    # the time_to_answer, comment submission date and current date.

    def setUp(self):
        # GIVEN organization in monitoring with answer time of 3 days
        self.org = mommy.make(Organization, name='org1', monitoring__time_to_answer=3)
        # AND score in approved task
        score = mommy.make(Score, task__status=Task.TASK_APPROVED, task__organization=self.org)

        # AND organization representative
        orguser = mommy.make(User)
        orguser.profile.organization.add(self.org)

        # AND today is 2014.08.14 10:25 (Thursday morning)
        patch('custom_comments.utils.datetime', Mock(today=lambda: datetime(2014, 8, 14, 10, 25))).start()

        # AND 4 comments by organization representative
        kwargs = dict(model=CommentExmo, status=CommentExmo.OPEN, object_pk=score.pk, user=orguser)

        # BUG 2178. Submitted at previous Thursday evening. Calcuations should ignore hours, use date only.
        mommy.make(submit_date=datetime(2014, 8, 7, 18, 31), **kwargs)  # expired

        mommy.make(submit_date=datetime(2014, 8, 8), **kwargs)          # expired
        mommy.make(submit_date=datetime(2014, 8, 11), **kwargs)         # urgent
        mommy.make(submit_date=datetime(2014, 8, 13), **kwargs)         # non-urgent

    def tearDown(self):
        patch.stopall()

    def test_open_comments_count(self):
        # WHEN comment report is constructed
        report = comment_report(self.org.monitoring)

        # THEN length of expired, urgent and non-urgent comments lists should be correct
        self.assertEqual(len(report['expired']), 2)
        self.assertEqual(len(report['urgent']), 1)
        self.assertEqual(len(report['non_urgent']), 1)


class PostCommentUnprivilegedAccessTestCase(OptimizedTestCase):
    # exmo2010:post_score_comment

    # Should forbid anonymous or unprivileged user to post score comments

    @classmethod
    def setUpClass(cls):
        super(PostCommentUnprivilegedAccessTestCase, cls).setUpClass()

        cls.users = {}
        cls.scores = {}
        # GIVEN scores in monitoring for every possible monitoring status
        for status, label in MONITORING_STATUS:
            param = mommy.make(Parameter, monitoring__status=status)
            task = mommy.make(Task, organization__monitoring=param.monitoring, status=Task.TASK_APPROVED)
            cls.score = mommy.make(Score, task=task, parameter=param, found=1)
            cls.scores[status] = cls.score
        # AND user without any permissions
        cls.users['user'] = User.objects.create_user('user', 'usr@svobodainfo.org', 'password')
        # AND anonymous user
        cls.users['anonymous'] = AnonymousUser()

    @parameterized.expand(MONITORING_STATUS)
    def test_forbid_post_comment_anonymous(self, status, *args):
        # WHEN anonymous user post comment
        request = Mock(user=self.users['anonymous'], method='POST',
                       POST={'score_%d-comment' % self.scores[status].pk: '123'})
        # THEN response should raise PermissionDenied exception
        self.assertRaises(PermissionDenied, post_score_comment, request, self.scores[status].pk)
        # AND new comments should not get created in db
        self.assertEqual(CommentExmo.objects.all().count(), 0)

    @parameterized.expand(MONITORING_STATUS)
    def test_forbid_post_comment_unprivileged(self, status, *args):
        # WHEN I am logged in as user without permissions and I post comment
        request = Mock(user=self.users['user'], method='POST',
                       POST={'score_%d-comment' % self.scores[status].pk: '123'})
        # THEN response should raise PermissionDenied exception
        self.assertRaises(PermissionDenied, post_score_comment, request, self.scores[status].pk)
        # AND new comments should not get created in db
        self.assertEqual(CommentExmo.objects.all().count(), 0)


class PostCommentTestCase(OptimizedTestCase):
    # exmo2010:post_score_comment

    # Should return corrected comment message when comment contain special characters (like ampersand).
    # BUG 2230. Improper handling of ampersand in comments.

    @classmethod
    def setUpClass(cls):
        super(PostCommentTestCase, cls).setUpClass()

        # GIVEN parameter in monitoring INTERACTION
        param = mommy.make(Parameter, monitoring__status=MONITORING_INTERACTION)
        # AND approved task
        cls.task = mommy.make(Task, organization__monitoring=param.monitoring, status=Task.TASK_APPROVED)
        # AND score
        cls.score = mommy.make(Score, task=cls.task, parameter=param, found=1)
        # AND expert A account
        cls.expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        cls.expertA.profile.is_expertA = True

    @parameterized.expand([
        ('<p>&id</p>', '<p>&amp;id</p>'),  # ampersand
        ('<p>&id;</p>', '<p>&amp;id;</p>'),  # ampersand and semicolon
        ('<p>modules.php?name=info&id=37</p>', '<p>modules.php?name=info&amp;id=37</p>'),  # ampersand in url
        ('<p>modules.php?name=info&amp;id=37</p>', '<p>modules.php?name=info&amp;id=37</p>'),  # from CKEditor
        ('<p>&nbsp;111</p>', '<p> 111</p>'),  # non-breakable space should be replaced with space
    ])
    @patch('scores.views.mail_comment', Mock())  # do not send emails
    def test_post_task_scores_table_settings_allow(self, original_message, expected_message):
        # WHEN I am logged in as expert A and I post comment
        request = Mock(user=self.expertA, method='POST', POST={'score_%d-comment' % self.score.pk: original_message})
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(post_score_comment(request, self.score.pk).status_code, 302)
        # AND new comment should get created in db
        # AND this comment should contain expected message
        self.assertEqual(CommentExmo.objects.filter(object_pk=self.score.pk).order_by('-id')[0].comment,
                         expected_message)


class CommentMailNotificationTestCase(TestCase):
    # When comment is posted, email should be sent to relevant users who have NOTIFICATION_ONEBYONE setting.

    def setUp(self):
        # GIVEN organization in interaction monitoring
        self.org = mommy.make(Organization, name='org2', monitoring__status=MONITORING_INTERACTION, inv_status='RGS')
        # AND corresponding parameter, and score for organization
        param = mommy.make(Parameter, monitoring=self.org.monitoring, weight=1)
        self.score = mommy.make(Score, task__status=Task.TASK_APPROVED, task__organization=self.org, parameter=param)

        # AND organization representative with NOTIFICATION_ONEBYONE email setting
        orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        orguser.groups.add(Group.objects.get(name=UserProfile.organization_group))
        profile = orguser.profile
        profile.organization = [self.org]
        profile.notification_type = UserProfile.NOTIFICATION_ONEBYONE
        profile.save()

        # AND expertA
        expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND I am logged in as expertA
        self.client.login(username='expertA', password='password')

    def test_mail_on_comment(self):
        url = reverse('exmo2010:post_score_comment', args=[self.score.pk])
        # WHEN I post comment to the score
        self.client.post(url, {'score_%s-comment' % self.score.pk: '123'})
        # THEN one email should be sent (to the representative of relevant organization)
        self.assertEqual(len(mail.outbox), 1)


class CommentsDigestTestCase(TestCase):
    # send_digest periodic task should work

    def setUp(self):
        # GIVEN expertA with NOTIFICATION_DIGEST setting enabled
        expertA = User.objects.create_user('expertA', 'user@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        expertA.profile.notification_type = UserProfile.NOTIFICATION_DIGEST
        expertA.profile.save()

        # AND score with comment
        score = mommy.make(Score)
        mommy.make(CommentExmo, object_pk=score.pk, content_type=ContentType.objects.get_for_model(Score))

    def test(self):
        # WHEN send_digest task is executed
        send_digest()

        # THEN 1 email should be sent
        self.assertEqual(len(mail.outbox), 1)
