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
from datetime import datetime, timedelta

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from model_mommy import mommy
from nose_parameterized import parameterized

from custom_comments.models import CommentExmo
from custom_comments.utils import comment_report

from exmo2010.celery_tasks import send_digest
from exmo2010.models.monitoring import Monitoring, MONITORING_PUBLISHED, MONITORING_INTERACTION, MONITORING_STATUS
from exmo2010.models import Organization, Parameter, Score, Task, UserProfile


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


class PostCommentUnprivilegedAccessTestCase(TestCase):
    # SHOULD forbid anonymous or unprivileged user to post score comments

    def setUp(self):
        self.score_urls = {}
        # GIVEN scores in monitoring for every possible monitoring status
        for status, label in MONITORING_STATUS:
            param = mommy.make(Parameter, monitoring__status=status)
            task = mommy.make(Task, organization__monitoring=param.monitoring, status=Task.TASK_APPROVED)
            score = mommy.make(Score, task=task, parameter=param, found=1)
            self.score_urls[status] = reverse('exmo2010:post_score_comment', args=[score.pk])
        # AND user without any permissions
        self.user = User.objects.create_user('user', 'user@svobodainfo.org', 'password')

    @parameterized.expand(MONITORING_STATUS)
    def test_forbid_post_comment_anonymous(self, status, *args):
        # WHEN I anonymous user post comment
        response = self.client.post(self.score_urls[status], {'comment': '123'})
        # THEN response status_code should be 403 (forbidden)
        self.assertEqual(response.status_code, 403)
        # AND new comments should not get created in db
        self.assertEqual(CommentExmo.objects.all().count(), 0)

    @parameterized.expand(MONITORING_STATUS)
    def test_forbid_post_comment_unprivileged(self, status, *args):
        # WHEN I am logged in as user without permissions
        self.client.login(username='user', password='password')
        # AND I post comment
        response = self.client.post(self.score_urls[status], {'comment': '123'})
        # THEN response status_code should be 403 (forbidden)
        self.assertEqual(response.status_code, 403)
        # AND new comments should not get created in db
        self.assertEqual(CommentExmo.objects.all().count(), 0)



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
