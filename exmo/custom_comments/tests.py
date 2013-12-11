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
import time

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from django.utils.crypto import salted_hmac
from model_mommy import mommy

from custom_comments.models import CommentExmo
from exmo2010.models import *


class PostCommentAccessTestCase(TestCase):
    # Scenario: SHOULD forbid unauthorized user to post score comments

    def setUp(self):
        self.client = Client()
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
