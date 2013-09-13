# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
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

from cStringIO import StringIO
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.utils import simplejson
from model_mommy import mommy
from nose_parameterized import parameterized
from core.sql import *
from exmo2010.models import *
from core.utils import UnicodeReader


class TestOpennessExpression(TestCase):
    def setUp(self):
        self.v1 = OpennessExpression.objects.get(code=1)
        self.v2 = mommy.make(OpennessExpression, code=2)
        self.v8 = OpennessExpression.objects.get(code=8)

    def test_sql_openness(self):
        self.assertEqual(self.v1.sql_openness(), sql_score_openness_v1)
        self.assertEqual(self.v8.sql_openness(), sql_score_openness_v8)
        self.assertRaises(Exception, self.v2.sql_monitoring)

    def test_sql_monitoring(self):
        self.assertEqual(self.v1.sql_monitoring(), sql_monitoring_v1)
        self.assertEqual(self.v8.sql_monitoring(), sql_monitoring_v8)
        self.assertRaises(Exception, self.v2.sql_monitoring)


class TestMonitoringExport(TestCase):
    # Scenario: Экспорт данных мониторинга
    def setUp(self):
        self.client = Client()
        # GIVEN предопределены все code OPENNESS_EXPRESSION
        for code in OpennessExpression.OPENNESS_EXPRESSIONS:
            # AND для каждого code есть опубликованный мониторинг
            monitoring = mommy.make(
                Monitoring,
                openness_expression__code=code,
                status=MONITORING_PUBLISHED)
            # AND в каждом мониторинге есть организация
            organization = mommy.make(Organization, monitoring=monitoring)
            # AND есть активный пользователь, не суперюзер, expert (см выше, этот - не эксперт, надо создать эксперта)
            expert = mommy.make_recipe('exmo2010.active_user')
            expert.profile.is_expertB = True
            # AND в каждой организации есть одобренная задача для expert
            task = mommy.make(
                Task,
                organization=organization,
                user=expert,
                status=Task.TASK_APPROVED,
            )
            # AND в каждом мониторинге есть параметр parameter с одним нерелевантным критерием
            parameter = mommy.make(
                Parameter,
                monitoring=monitoring,
                complete=False,
            )
            # AND в каждой задаче есть оценка по parameter
            score = mommy.make(
                Score,
                task=task,
                parameter=parameter,
            )
            score = mommy.make(
                Score,
                task=task,
                parameter=parameter,
                revision=Score.REVISION_INTERACT,
            )

    def parameter_type(self, score):
        return 'npa' if score.parameter.npa else 'other'

    @parameterized.expand(
        [("expression-v%d" % code, code)
            for code in OpennessExpression.OPENNESS_EXPRESSIONS])
    def test_json(self, name, code):
        monitoring = Monitoring.objects.get(openness_expression__code=code)
        # WHEN анонимный пользователь запрашивает данные каждого мониторинга в json
        url = reverse('exmo2010:monitoring_export', args=[monitoring.pk])
        response = self.client.get(url + '?format=json')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается json
        self.assertEqual(response.get('content-type'), 'application/json')
        json = simplejson.loads(response.content)
        organization = monitoring.organization_set.all()[0]
        task = organization.task_set.all()[0]
        score = task.score_set.filter(revision=Score.REVISION_DEFAULT,)[0]
        # AND имя мониторинга в БД и json совпадает
        self.assertEqual(json['monitoring']['name'], monitoring.name)
        # AND имя организации (для первой задачи) в БД и json совпадает
        self.assertEqual(
            json['monitoring']['tasks'][0]['name'],
            organization.name)
        # AND КИД (для первой задачи) в БД и json совпадает
        self.assertEqual(
            float(json['monitoring']['tasks'][0]['openness']),
            float('%.3f' % task.openness))
        # AND балл найденности (в первой задаче, в оценке по первому параметру)
        # в БД и json совпадает
        self.assertEqual(
            int(json['monitoring']['tasks'][0]['scores'][0]['found']),
            int(score.found))
        self.assertEqual(
            json['monitoring']['tasks'][0]['scores'][0]['type'],
            self.parameter_type(score)
        )

    @parameterized.expand(
        [("expression-v%d" % code, code)
            for code in OpennessExpression.OPENNESS_EXPRESSIONS])
    def test_csv(self, name, code):
        monitoring = Monitoring.objects.get(openness_expression__code=code)
        # WHEN анонимный пользователь запрашивает данные каждого мониторинга в csv
        url = reverse('exmo2010:monitoring_export', args=[monitoring.pk])
        response = self.client.get(url + '?format=csv')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается csv
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        csv = UnicodeReader(StringIO(response.content))
        organization = monitoring.organization_set.all()[0]
        task = organization.task_set.all()[0]
        row_count = 0
        for row in csv:
            row_count += 1
            self.assertEqual(len(row), 18)
            if row_count == 1:
                self.assertEqual(row[0], '#Monitoring')
                continue
            else:
                revision = row[17]
                self.assertIn(revision, Score.REVISION_EXPORT.values())
                for k, v in Score.REVISION_EXPORT.iteritems():
                    if v == revision:
                        revision = k
                        break
                score = task.score_set.filter(revision=revision)[0]
                # AND имя мониторинга в БД и json совпадает
                self.assertEqual(row[0], monitoring.name)
                # AND имя организации (для первой задачи) в БД и json совпадает
                self.assertEqual(
                    row[1],
                    organization.name)
                self.assertEqual(
                    int(row[2]),
                    organization.pk)
                # AND КИД (для первой задачи) в БД и json совпадает
                self.assertEqual(
                    float(row[5]),
                    float(task.openness))
                self.assertEqual(
                    float(row[7]),
                    float(score.parameter.pk))
                # AND балл найденности (в первой задаче, в оценке по первому параметру)
                # в БД и json совпадает
                self.assertEqual(
                    int(row[8]),
                    int(score.found))
                self.assertEqual(
                    row[16],
                    self.parameter_type(score)
                )

class TestMonitoringExportApproved(TestCase):
    # Scenario: Экспорт данных мониторинга
    def setUp(self):
        self.client = Client()
        self.monitoring = mommy.make(
            Monitoring,
            pk=999,
            status=MONITORING_PUBLISHED)
        # AND в каждом мониторинге есть организация
        organization = mommy.make(Organization, monitoring=self.monitoring)
        # AND есть активный пользователь, не суперюзер, expert (см выше, этот - не эксперт, надо создать эксперта)
        expert1 = mommy.make_recipe('exmo2010.active_user')
        expert1.profile.is_expertB = True
        expert2 = mommy.make_recipe('exmo2010.active_user')
        expert2.profile.is_expertB = True
        # AND в каждой организации есть одобренная задача для expert
        task = mommy.make(
            Task,
            organization=organization,
            user=expert1,
            status=Task.TASK_APPROVED,
        )
        task = mommy.make(
            Task,
            organization=organization,
            user=expert2,
            status=Task.TASK_OPEN,
        )
        # AND в каждом мониторинге есть параметр parameter с одним нерелевантным критерием
        parameter = mommy.make(
            Parameter,
            monitoring=self.monitoring,
            complete=False)
        # AND в каждой задаче есть оценка по parameter
        score = mommy.make(
            Score,
            task=task,
            parameter=parameter,
        )

    def test_approved_json(self):
        url = reverse('exmo2010:monitoring_export', args=[self.monitoring.pk])
        response = self.client.get(url + '?format=json')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается json
        self.assertEqual(response.get('content-type'), 'application/json')
        json = simplejson.loads(response.content)
        self.assertEqual(len(json['monitoring']['tasks']), 0, simplejson.dumps(json, indent=2))

    def test_approved_csv(self):
        url = reverse('exmo2010:monitoring_export', args=[self.monitoring.pk])
        response = self.client.get(url + '?format=csv')
        # THEN запрос удовлетворяется
        self.assertEqual(response.status_code, 200)
        # AND отдается csv
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        csv = [line for line in UnicodeReader(StringIO(response.content))]
        #only header
        self.assertEqual(len(csv), 1)
