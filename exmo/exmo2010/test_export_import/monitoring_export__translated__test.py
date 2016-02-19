# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2016 IRSI LTD
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
from __future__ import unicode_literals

import json
from cStringIO import StringIO

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy
from nose_parameterized import parameterized

from core.utils import UnicodeReader
from exmo2010.models import Monitoring, Organization, Parameter, Task, Score
from exmo2010.models.monitoring import PUB


class TranslatedMonitoringScoresDataExportTestCase(TestCase):
    # exmo2010:monitoring_export

    # Should export content in a different languages

    def setUp(self):
        # GIVEN published monitoring with 1 organization
        self.monitoring = mommy.make(Monitoring, status=PUB, name_en='monitoring', name_ru=u'мониторинг')
        self.organization = mommy.make(Organization, monitoring=self.monitoring, name_en='organization', name_ru=u'организация')
        # AND expert B account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND 2 users accounts with different languages
        user_en = User.objects.create_user('user_en', 'en_user@svobodainfo.org', 'password')
        user_en.profile.language = 'en'
        user_en.profile.save()
        user_ru = User.objects.create_user('user_ru', 'ru_user@svobodainfo.org', 'password')
        user_ru.profile.language = 'ru'
        user_ru.profile.save()
        # AND approved task assigned to expert B
        task = mommy.make(Task, organization=self.organization, user=expertB, status=Task.TASK_APPROVED,)
        # AND 1 parameter
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=1, name_en='parameter', name_ru=u'параметр')
        # AND 2 scores
        mommy.make(Score, task=task, parameter=self.parameter)
        mommy.make(Score, task=task, parameter=self.parameter, revision=Score.REVISION_INTERACT)
        self.url = reverse('exmo2010:monitoring_export', args=[self.monitoring.pk])

    @parameterized.expand([
        ('ru',),
        ('en',),
    ])
    def test_json(self, lang):
        # WHEN I am logged in as user
        self.client.login(username='user_%s' % lang, password='password')
        # AND I get json-file from response for current monitoring
        response = self.client.get(self.url + '?format=json', follow=True)
        json_file = json.loads(response.content)
        # THEN monitoring, organization and parameter names should be in user preferable language
        field = 'name_%s' % lang
        self.assertEqual(json_file['monitoring']['name'], getattr(self.monitoring, field))
        self.assertEqual(json_file['monitoring']['tasks'][0]['name'], getattr(self.organization, field))
        self.assertEqual(json_file['monitoring']['tasks'][0]['scores'][0]['name'], getattr(self.parameter, field))

    @parameterized.expand([
        ('ru',),
        ('en',),
    ])
    def test_csv(self, lang):
        # WHEN I am logged in as user
        self.client.login(username='user_%s' % lang, password='password')
        # AND I get csv-file from response for current monitoring
        response = self.client.get(self.url + '?format=csv', follow=True)
        csv = UnicodeReader(StringIO(response.content))
        field = 'name_%s' % lang
        for count, row in enumerate(csv, 1):
            if count != 1 and not row[0].startswith('#'):
                # THEN monitoring, organization and parameter names should be in user preferable language
                self.assertEqual(row[0], getattr(self.monitoring, field))
                self.assertEqual(row[1], getattr(self.organization, field))
                self.assertEqual(row[6], getattr(self.parameter, field))
