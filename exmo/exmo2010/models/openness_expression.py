# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _

from core.sql import (
    sql_parameter_filter, sql_revision_filter, sql_task_openness, sql_score_openness_initial_v1,
    sql_score_openness_v1, sql_score_openness_initial_v8, sql_score_openness_v8, sql_monitoring_v1, sql_monitoring_v8)
from .base import BaseModel
from .parameter import Parameter


class OpennessExpression(BaseModel):
    """
    Openness expression model for code and name of openness.

    """
    code = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=255, default="-", verbose_name=_('name'))

    OPENNESS_EXPRESSIONS = [1, 8]

    def __unicode__(self):
        result = '%(name)s (%(prep)s EXMO2010 v%(code)d)' % \
                 {'name': self.name, 'prep': _('from'), 'code': self.code}

        return result

    def get_sql_openness(self, parameters=None, initial=False):
        """
        Getting raw SQL for 'openness' (if initial=False) or
        'openness initial' (if initial=True). Calculating for all
        parameters (by default) and using with '.extra(select=...)'
        expression.

        """
        score_openness = self.get_sql_expression(initial=initial)
        revision_filter = "" if initial else sql_revision_filter
        parameter_filter = ""
        if parameters:
            if isinstance(parameters[0], Parameter):
                parameters = [p.pk for p in parameters]
            parameter_filter = sql_parameter_filter % ','.join(str(p) for p in parameters)
        result = sql_task_openness % {
            'sql_score_openness': score_openness,
            'sql_revision_filter': revision_filter,
            'sql_parameter_filter': parameter_filter,
        }

        return result

    def get_sql_expression(self, initial=False):
        if self.code == 1:
            result = initial and sql_score_openness_initial_v1 or sql_score_openness_v1
        elif self.code == 8:
            result = initial and sql_score_openness_initial_v8 or sql_score_openness_v8
        else:
            raise ValidationError(ugettext('Unknown OpennessExpression code'))

        return result

    def sql_monitoring(self):
        if self.code == 1:
            return sql_monitoring_v1
        elif self.code == 8:
            return sql_monitoring_v8
        else:
            raise ValidationError(ugettext('Unknown OpennessExpression code'))
