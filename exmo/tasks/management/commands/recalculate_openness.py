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
from django.core.management.base import BaseCommand, CommandError

from core.sql import sql_score_openness_v1, sql_score_openness_v8
from exmo2010.models import Task


sql_tail = """
*
if (exmo2010_score.revision=0,
        (NOT EXISTS (SELECT SC.`id`
        FROM `exmo2010_score` SC
        WHERE SC.`parameter_id`=exmo2010_score.parameter_id
        AND SC.`task_id`=exmo2010_score.task_id
        AND SC.`revision`=1)),
    1)
"""


SQL_score_openness_v1 = sql_score_openness_v1 + sql_tail
SQL_score_openness_v8 = sql_score_openness_v8 + sql_tail


SQL_task_openness = """
(SELECT (SUM(
%(sql_score_openness)s
)*100)
FROM `exmo2010_score`
join exmo2010_parameter on exmo2010_score.parameter_id=exmo2010_parameter.id
WHERE (
    `exmo2010_score`.`task_id` = exmo2010_task.id AND
    `exmo2010_score`.`parameter_id` IN
    (SELECT U0.`id`
    FROM `exmo2010_parameter` U0
    WHERE `exmo2010_parameter`.`monitoring_id` = exmo2010_organization.monitoring_id
    AND NOT ((`exmo2010_parameter`.`id` IN
        (SELECT U1.`parameter_id`
        FROM `exmo2010_parameter_exclude` U1
        WHERE (U1.`organization_id` = exmo2010_task.organization_id
        AND U1.`parameter_id` IS NOT NULL))
        AND `exmo2010_parameter`.`id` IS NOT NULL))))
)
/
(SELECT sum(exmo2010_parameter.weight)
FROM `exmo2010_parameter`
WHERE (
    `exmo2010_parameter`.`weight` >= 0
    AND `exmo2010_parameter`.`monitoring_id` = exmo2010_organization.monitoring_id
    AND NOT ((`exmo2010_parameter`.`id` IN (
        SELECT U1.`parameter_id`
        FROM `exmo2010_parameter_exclude` U1
        WHERE (U1.`organization_id` = exmo2010_organization.id
            AND U1.`parameter_id` IS NOT NULL))
        AND `exmo2010_parameter`.`id` IS NOT NULL))
    )
)
"""


def sql_openness(task):
    code = task.organization.monitoring.openness_expression.code
    sql_score_openness = SQL_score_openness_v1 if code == 1 else SQL_score_openness_v8
    result = SQL_task_openness % {'sql_score_openness': sql_score_openness}

    return result


def get_openness(task):
    result = Task.objects.filter(pk=task.pk)\
                         .extra(select={'__openness': sql_openness(task)})\
                         .values('__openness')[0]['__openness'] or 0

    return result


class Command(BaseCommand):
    args = '<monitoring_id monitoring_id ...>'

    def handle(self, *args, **options):
        if not args:
            raise CommandError('Enter monitoring ID in command line!')
        for monitoring_id in args:
            try:
                tasks = Task.objects.filter(organization__monitoring=monitoring_id)
            except Task.DoesNotExist:
                raise CommandError('Tasks for monitoring "%s" does not exists' % monitoring_id)

            for task in tasks:
                task.openness_first = get_openness(task)
                task.save()

            self.stdout.write('Successfully closed monitoring "%s"\n' % monitoring_id)
