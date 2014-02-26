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
import time

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.crypto import salted_hmac
from model_mommy import mommy

from custom_comments.models import CommentExmo
from custom_comments.utils import comment_report
from exmo2010.models import (Monitoring, Organization, Parameter, Score, Task,
                             MONITORING_PUBLISHED, MONITORING_INTERACTION)


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


class CommentGetQueryAccessTestCase(TestCase):
    # Scenario: should disallow to send get-query

    def test_anonymous_send_get_query(self):
        # WHEN anonymous user send GET-query
        url = reverse('comments-post-comment')
        response = self.client.get(url, follow=True)
        # THEN response status_code should be 405 (Method Not Allowed)
        self.assertEqual(response.status_code, 405)


class PostCommentAccessTestCase(TestCase):
    # Scenario: SHOULD forbid unauthorized user to post score comments

    def setUp(self):
        self.site = Site.objects.get_current()
        self.content_type = ContentType.objects.get_for_model(Score)

        # GIVEN interaction monitoring
        monitoring = mommy.make(Monitoring, status=MONITORING_INTERACTION)
        # AND organization connected to interaction monitoring
        self.organization = mommy.make(Organization, monitoring=monitoring)
        # AND corresponding task, parameter, and score for organization
        task = mommy.make(Task, organization=self.organization, status=Task.TASK_APPROVED)
        parameter = mommy.make(Parameter, monitoring=monitoring)
        self.score = mommy.make(Score, task=task, parameter=parameter, found=1)
        # AND user without any permissions
        self.user = User.objects.create_user('user', 'user@svobodainfo.org', 'password')

    def test_post_comment_access(self):
        # WHEN I am logged in as user without permissions
        self.client.login(username='user', password='password')
        # AND I post comment
        url = reverse('login-required-post-comment')
        key_salt = "django.contrib.forms.CommentSecurityForm"
        timestamp = str(int(time.time()))
        object_pk = str(self.score.pk)
        content_type = '.'.join([self.content_type.app_label, self.content_type.model])
        value = "-".join([content_type, object_pk, timestamp])
        security_hash = salted_hmac(key_salt, value).hexdigest()
        data = {
            'status': '0',
            'comment': 'Comment',
            'timestamp': timestamp,
            'object_pk': object_pk,
            'security_hash': security_hash,
            'content_type': content_type,
        }
        response = self.client.post(url, data, follow=True)
        # THEN response status_code should be 403 (forbidden)
        self.assertEqual(response.status_code, 403)
        # AND new comments shouldn't be existed
        count_comments = CommentExmo.objects.all().count()
        self.assertEqual(count_comments, 0)
