# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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

"""
Модуль в котором хранится RAW SQL
"""

#Расчёт Кид для одной оценки по формуле v1
sql_score_openness_v1 = """
exmo2010_parameter.weight*
exmo2010_score.found*
if (exmo2010_parameter.complete=1,
	(CASE exmo2010_score.complete
	WHEN 1 THEN 0.2
	WHEN 2 THEN 0.5
    ELSE 1
	END),
	1)*
if (exmo2010_parameter.topical=1,
	(CASE exmo2010_score.topical
	WHEN 1 THEN 0.7
	WHEN 2 THEN 0.85
    ELSE 1
	END),
	1)*
if (exmo2010_parameter.accessible=1,
	(CASE exmo2010_score.accessible
	WHEN 1 THEN 0.9
	WHEN 2 THEN 0.95
    ELSE 1
	END),
	1)*
if (exmo2010_parameter.hypertext=1,
	if (exmo2010_parameter.document=1,
	    (CASE exmo2010_score.hypertext
	    WHEN 0 THEN 0.2
	    WHEN 1 THEN
	        (CASE exmo2010_score.document
	        WHEN 0 THEN 0.9
	        ELSE 1
	        END)
	    ELSE 1
	    END),
        (CASE exmo2010_score.hypertext
        WHEN 0 THEN 0.2
	    ELSE 1
	    END)
	    ),
	1)
"""

#Расчёт Кид для одной оценки по формуле v8
sql_score_openness_v8 = """
exmo2010_parameter.weight*
exmo2010_score.found*
if (exmo2010_parameter.complete=1,
	(CASE exmo2010_score.complete
	WHEN 1 THEN 0.2
	WHEN 2 THEN 0.5
    ELSE 1
	END),
	1)*
if (exmo2010_parameter.topical=1,
	(CASE exmo2010_score.topical
	WHEN 1 THEN 0.7
	WHEN 2 THEN 0.85
    ELSE 1
	END),
	1)*
if (exmo2010_parameter.accessible=1,
	(CASE exmo2010_score.accessible
	WHEN 1 THEN 0.9
	WHEN 2 THEN 0.95
    ELSE 1
	END),
	1)*
if (exmo2010_parameter.hypertext=1,
	(CASE exmo2010_score.hypertext
	WHEN 0 THEN 0.2
    ELSE 1
	END),
	1)*
if (exmo2010_parameter.document=1,
	(CASE exmo2010_score.document
	WHEN 0 THEN 0.85
    ELSE 1
	END),
	1)*
if (exmo2010_parameter.image=1,
	(CASE exmo2010_score.image
	WHEN 0 THEN 0.95
    ELSE 1
	END),
	1)
"""


#Расчет Кид для задачи
sql_task_openness = """
(SELECT (SUM(
%(sql_score_openness)s
)*100)
FROM `exmo2010_score`
join exmo2010_parameter on exmo2010_score.parameter_id=exmo2010_parameter.id
WHERE (
	`exmo2010_score`.`task_id` = exmo2010_task.id AND
	`exmo2010_score`.`revision` = 0  AND
	`exmo2010_score`.`parameter_id` IN
	(SELECT
		U0.`id`
	FROM `exmo2010_parameter` U0
	WHERE `exmo2010_parameter`.`monitoring_id` = exmo2010_organization.monitoring_id
    %(sql_parameter_filter)s
	AND NOT ((`exmo2010_parameter`.`id` IN
		(SELECT U1.`parameter_id`
		FROM `exmo2010_parameter_exclude` U1
		WHERE (U1.`organization_id` = exmo2010_task.organization_id
		AND U1.`parameter_id` IS NOT NULL))
		AND `exmo2010_parameter`.`id` IS NOT NULL))))
)
/
(SELECT
    sum(exmo2010_parameter.weight)
FROM `exmo2010_parameter`
WHERE (
    `exmo2010_parameter`.`weight` >= 0
    AND `exmo2010_parameter`.`monitoring_id` = exmo2010_organization.monitoring_id
    %(sql_parameter_filter)s
    AND NOT ((`exmo2010_parameter`.`id` IN (
        SELECT U1.`parameter_id`
        FROM `exmo2010_parameter_exclude` U1
        WHERE (U1.`organization_id` = exmo2010_organization.id
            AND U1.`parameter_id` IS NOT NULL))
        AND `exmo2010_parameter`.`id` IS NOT NULL))
    )
)
"""
