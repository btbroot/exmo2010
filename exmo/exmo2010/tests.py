# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013 Foundation "Institute for Information Freedom Development"
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
from django.test import TestCase
from model_mommy import mommy
from nose_parameterized import parameterized

from core.sql import *
from exmo2010.models import *


class TestMonitoring(TestCase):
    # Scenario: monitoring model test

    @parameterized.expand([(code,) for code in OpennessExpression.OPENNESS_EXPRESSIONS])
    def test_sql_scores_valid(self, code):
        # WHEN openness code in allowable range
        monitoring = mommy.make(Monitoring, openness_expression__code=code)
        openness = monitoring.openness_expression
        expected_result = sql_monitoring_scores % {
            'sql_monitoring': openness.sql_monitoring(),
            'sql_openness_initial': openness.get_sql_openness(initial=True),
            'sql_openness': openness.get_sql_openness(),
            'monitoring_pk': monitoring.pk,
        }
        # THEN function return expected result
        self.assertEqual(monitoring.sql_scores(), expected_result)

    @parameterized.expand([(2,)])
    def test_sql_scores_invalid(self, code):
        # WHEN openness code in disallowable range
        monitoring = mommy.make(Monitoring, openness_expression__code=code)
        # THEN raises exception
        self.assertRaises(ValidationError, monitoring.sql_scores)


class TestOpennessExpression(TestCase):
    # Scenario: openness expression model test
    parameters_count = 10
    empty_string = ""
    revision_filter = sql_revision_filter
    parameter_filter = sql_parameter_filter % ','.join(str(i) for i in range(1, parameters_count + 1))

    def setUp(self):
        # GIVEN 2 openness expressions with valid code
        self.v1 = mommy.make(OpennessExpression, code=1)
        self.v8 = mommy.make(OpennessExpression, code=8)
        # AND 1 openness expression with invalid code
        self.v2 = mommy.make(OpennessExpression, code=2)
        # AND any 10 parameters objects
        self.parameters = mommy.make(Parameter, _quantity=self.parameters_count)

    @parameterized.expand([
        ({}, [sql_score_openness_v1, revision_filter, empty_string]),
        ({'initial': True}, [sql_score_openness_initial_v1, empty_string, empty_string]),
        ({'parameters': True}, [sql_score_openness_v1, revision_filter, parameter_filter]),
        ({'parameters': True, 'initial': True}, [sql_score_openness_initial_v1, empty_string, parameter_filter]),
    ])
    def test_get_sql_openness_valid_v1(self, kwargs, args):
        # WHEN openness code in allowable range
        if kwargs.get('parameters', False):
            kwargs['parameters'] = self.parameters

        # THEN function return expected result
        self.assertEqual(self.v1.get_sql_openness(**kwargs),
                         self.expected_result(*args))

    @parameterized.expand([
        ({}, [sql_score_openness_v8, revision_filter, empty_string]),
        ({'initial': True}, [sql_score_openness_initial_v8, empty_string, empty_string]),
        ({'parameters': True}, [sql_score_openness_v8, revision_filter, parameter_filter]),
        ({'parameters': True, 'initial': True}, [sql_score_openness_initial_v8, empty_string, parameter_filter]),
    ])
    def test_get_sql_openness_valid_v1(self, kwargs, args):
        # WHEN openness code in allowable range
        if kwargs.get('parameters', False):
            kwargs['parameters'] = self.parameters

        # THEN function return expected result
        self.assertEqual(self.v8.get_sql_openness(**kwargs),
                         self.expected_result(*args))

    @parameterized.expand([
        ({},),
        ({'initial': True},),
        ({'parameters': True},),
        ({'parameters': True, 'initial': True},),
    ])
    def test_get_sql_openness_invalid(self, kwargs):
        # WHEN openness code is invalid
        if kwargs.get('parameters', False):
            kwargs['parameters'] = self.parameters

        # THEN raises exception
        self.assertRaises(ValidationError, self.v2.get_sql_openness, **kwargs)

    def expected_result(self, sql_score_openness, sql_revision_filter, sql_parameter_filter):
        result = sql_task_openness % {
            'sql_score_openness': sql_score_openness,
            'sql_revision_filter': sql_revision_filter,
            'sql_parameter_filter': sql_parameter_filter,
        }

        return result

    @parameterized.expand([
        (1, {}, sql_score_openness_v1),
        (8, {}, sql_score_openness_v8),
        (1, {'initial': True}, sql_score_openness_initial_v1),
        (8, {'initial': True}, sql_score_openness_initial_v8),
    ])
    def test_get_sql_expression_valid(self, code, kwargs, args):
        # WHEN openness code in allowable range
        # THEN function return expected result
        openness = getattr(self, 'v%d' % code)
        self.assertEqual(openness.get_sql_expression(kwargs), args)

    @parameterized.expand([
        ({},),
        ({'initial': True},),
    ])
    def test_get_sql_expression_invalid(self, kwargs):
        # WHEN openness code is invalid
        # THEN raises exception
        self.assertRaises(ValidationError, self.v2.get_sql_expression, **kwargs)

    @parameterized.expand([
        (1, sql_monitoring_v1),
        (8, sql_monitoring_v8),
    ])
    def test_sql_monitoring_valid(self, code, result):
        # WHEN openness code in allowable range
        # THEN function return expected result
        openness = getattr(self, 'v%d' % code)
        self.assertEqual(openness.sql_monitoring(), result)

    def test_sql_monitoring_invalid(self):
        # WHEN openness code is invalid
        # THEN raises exception
        self.assertRaises(ValidationError, self.v2.sql_monitoring)
