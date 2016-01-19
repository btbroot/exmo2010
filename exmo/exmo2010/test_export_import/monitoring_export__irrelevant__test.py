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
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy
from nose_parameterized import parameterized

from exmo2010.models import (Monitoring, OpennessExpression, Organization, Parameter, Task, Score)
from exmo2010.models.monitoring import PUB


class MonitoringExportIrrelevantTestCase(TestCase):
    # exmo2010:monitoring_export

    # In JSON export, irrelevant criteria of scores should be omitted.
    # In CSV export, irrelevant criteria of scores should have value "not relevant".

    def setUp(self):
        for code in OpennessExpression.OPENNESS_EXPRESSIONS:
            # GIVEN PUBLISHED monitoring
            monitoring = mommy.make(Monitoring, openness_expression__code=code, status=PUB, name='mv%d' % code)
            # AND organization
            org = mommy.make(Organization, monitoring=monitoring, name='org')
            # AND approved task
            task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)
            # AND parameter, with all criteria relevant, except "complete"
            parameter = mommy.make(Parameter, monitoring=monitoring, complete=False, weight=1, name='p')
            # AND score
            mommy.make(Score, task=task, parameter=parameter, found=1, links='link', recommendations='yep')

    expected_json = {
        1: {'monitoring': {
            'name': 'mv1',
            'tasks': [
                {
                    'id': 1,
                    'name': 'org',
                    'openness': '100.000',
                    'openness_initial': '100.000',
                    'position': 1,
                    'url': None,
                    'scores': [{
                            # "complete" should be omitted
                            'accessible': 0,
                            'found': 1,
                            'hypertext': 0,
                            'id': 1,
                            'links': 'link',
                            'name': 'p',
                            'recommendations': 'yep',
                            'revision': 'default',
                            'social': 1,
                            'topical': 0,
                            'type': 'other'}]
                }]}},
        8: {'monitoring': {
            'name': 'mv8',
            'tasks': [
                {
                    'id': 2,
                    'name': 'org',
                    'openness': '100.000',
                    'openness_initial': '100.000',
                    'position': 1,
                    'url': None,
                    'scores': [{
                            # "complete" should be omitted
                            'accessible': 0,
                            'document': 0,
                            'found': 1,
                            'hypertext': 0,
                            'id': 2,
                            'image': 0,
                            'links': 'link',
                            'name': 'p',
                            'recommendations': 'yep',
                            'revision': 'default',
                            'social': 1,
                            'topical': 0,
                            'type': 'other'}]
                }]}}
    }

    CSV_HEAD = ','.join([
        '#Monitoring', 'Organization', 'Organization_id', 'Position', 'Initial Openness', 'Openness',
        'Parameter', 'Parameter_id', 'Found', 'Complete', 'Topical', 'Accessible', 'Hypertext', 'Document',
        'Image', 'Social', 'Type', 'Revision', 'Links', 'Recommendations'])

    expected_csv = {
        # For v1 "complete" criterion should be "not relevant", as well as "Document" and "Image" (does not exist in v1)
        1: CSV_HEAD + '\r\nmv1,org,1,1,100.000,100.000,p,1,1,not relevant,0.0,0.0,0.0,not relevant,not relevant,1,other,default,link,yep\r\n#\r\n',
        # For v8 "complete" criterion should be "not relevant"
        8: CSV_HEAD + '\r\nmv8,org,2,1,100.000,100.000,p,2,1,not relevant,0.0,0.0,0.0,0.0,0.0,1,other,default,link,yep\r\n#\r\n'
    }

    @parameterized.expand(zip(OpennessExpression.OPENNESS_EXPRESSIONS))
    def test_json(self, code):
        monitoring = Monitoring.objects.get(openness_expression__code=code)
        # WHEN user gets monitoring exported as JSON
        url = reverse('exmo2010:monitoring_export', args=[monitoring.pk])
        response = self.client.get(url + '?format=json')
        # THEN response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND response content-type is "application/json"
        self.assertEqual(response.get('content-type'), 'application/json')
        # AND JSON content has irrelevant criteria excluded from scores
        self.assertEqual(self.expected_json[code], json.loads(response.content))

    @parameterized.expand(zip(OpennessExpression.OPENNESS_EXPRESSIONS))
    def test_csv(self, code):
        monitoring = Monitoring.objects.get(openness_expression__code=code)
        # WHEN user gets monitoring exported as CSV
        url = reverse('exmo2010:monitoring_export', args=[monitoring.pk])
        response = self.client.get(url + '?format=csv')
        # THEN response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND response content-type is "application/vnd.ms-excel"
        self.assertEqual(response.get('content-type'), 'application/vnd.ms-excel')
        # AND CSV content has irrelevant criteria marked with "not relevant" values
        self.assertEqual(self.expected_csv[code], response.content.decode('utf16'))
