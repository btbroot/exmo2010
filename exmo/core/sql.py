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
from django.utils.translation import get_language
from modeltranslation.utils import resolution_order


# Calculate Openness for each score (with openness code = 1)
sql_score_openness_v1 = """
exmo2010_parameter.weight*
exmo2010_score.found*
(CASE exmo2010_parameter.complete
    WHEN 1 THEN
        (CASE exmo2010_score.complete
        WHEN 1 THEN 0.2
        WHEN 2 THEN 0.5
        ELSE 1
        END)
    ELSE 1
    END)*
(CASE exmo2010_parameter.topical
    WHEN 1 THEN
        (CASE exmo2010_score.topical
        WHEN 1 THEN 0.7
        WHEN 2 THEN 0.85
        ELSE 1
        END)
    ELSE 1
    END)*
(CASE exmo2010_parameter.accessible
    WHEN 1 THEN
        (CASE exmo2010_score.accessible
        WHEN 1 THEN 0.9
        WHEN 2 THEN 0.95
        ELSE 1
        END)
    ELSE 1
    END)*
(CASE exmo2010_parameter.hypertext
    WHEN 1 THEN
        (CASE exmo2010_parameter.document
            WHEN 1 THEN
                (CASE exmo2010_score.hypertext
                WHEN 0 THEN 0.2
                WHEN 1 THEN
                    (CASE exmo2010_score.document
                    WHEN 0 THEN 0.9
                    ELSE 1
                    END)
                ELSE 1
                END)
            ELSE
                (CASE exmo2010_score.hypertext
                WHEN 0 THEN 0.2
                ELSE 1
                END)
            END)
    ELSE 1
    END)
"""

# Calculate Openness for each score (with openness code = 8)
sql_score_openness_v8 = """
exmo2010_parameter.weight*
exmo2010_score.found*
(CASE exmo2010_parameter.complete
    WHEN 1 THEN
        (CASE exmo2010_score.complete
        WHEN 1 THEN 0.2
        WHEN 2 THEN 0.5
        ELSE 1
        END)
    ELSE 1
    END)*
(CASE exmo2010_parameter.topical
    WHEN 1 THEN
        (CASE exmo2010_score.topical
        WHEN 1 THEN 0.7
        WHEN 2 THEN 0.85
        ELSE 1
        END)
    ELSE 1
    END)*
(CASE exmo2010_parameter.accessible
    WHEN 1 THEN
        (CASE exmo2010_score.accessible
        WHEN 1 THEN 0.9
        WHEN 2 THEN 0.95
        ELSE 1
        END)
    ELSE 1
    END)*
(CASE exmo2010_parameter.hypertext
    WHEN 1 THEN
        (CASE exmo2010_score.hypertext
        WHEN 0 THEN 0.2
        ELSE 1
        END)
    ELSE 1
    END)*
(CASE exmo2010_parameter.document
    WHEN 1 THEN
        (CASE exmo2010_score.document
        WHEN 0 THEN 0.85
        ELSE 1
        END)
    ELSE 1
    END)*
(CASE exmo2010_parameter.image
    WHEN 1 THEN
        (CASE exmo2010_score.image
        WHEN 0 THEN 0.95
        ELSE 1
        END)
    ELSE 1
    END)
"""

# Return 1 if current score revision = 1
# or the same score with revision = 1 exists in scores table
sql_tail_with_respect_to_revision = """
* (CASE exmo2010_score.revision
    WHEN 0 THEN
        (NOT EXISTS (SELECT SC.`id`
        FROM `exmo2010_score` SC
        WHERE SC.`parameter_id`=exmo2010_score.parameter_id
        AND SC.`task_id`=exmo2010_score.task_id
        AND SC.`revision`=1))
    ELSE 1
END)
"""

# Calculate Openness Initial for each score (with openness code = 1)
sql_score_openness_initial_v1 = sql_score_openness_v1 + sql_tail_with_respect_to_revision


# Calculate Openness Initial for each score (with openness code = 8)
sql_score_openness_initial_v8 = sql_score_openness_v8 + sql_tail_with_respect_to_revision


# Calculate Openness (or Openness Initial):
sql_task_openness = """
(SELECT (SUM(
%(sql_score_openness)s
)*100)
FROM `exmo2010_score`
join exmo2010_parameter on exmo2010_score.parameter_id=exmo2010_parameter.id
WHERE (
    `exmo2010_score`.`task_id` = exmo2010_task.id AND
    %(sql_revision_filter)s
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

# Filter for revisions = 0 only
sql_revision_filter = "`exmo2010_score`.`revision` = 0  AND"

# Filter for chosen parameters only
sql_parameter_filter = "AND `exmo2010_parameter`.`id` in (%s)"


#расчёт complete
sql_complete_parameters = """
SELECT
    COUNT(`exmo2010_parameter`.`id`)
FROM `exmo2010_parameter`
WHERE (
    `exmo2010_parameter`.`monitoring_id` = `exmo2010_organization`.`monitoring_id`
    AND NOT ((
        `exmo2010_parameter`.`id` IN (
            SELECT U1.`parameter_id`
            FROM `exmo2010_parameter_exclude` U1
            WHERE (U1.`organization_id` = `exmo2010_task`.organization_id
                AND U1.`parameter_id` IS NOT NULL))
            AND `exmo2010_parameter`.`id` IS NOT NULL))
    )
"""

sql_complete_questions = """
SELECT
    COUNT(`exmo2010_qquestion`.`id`)
FROM `exmo2010_qquestion`
INNER JOIN `exmo2010_questionnaire` ON (`exmo2010_qquestion`.`questionnaire_id` = `exmo2010_questionnaire`.`id`)
WHERE `exmo2010_questionnaire`.`monitoring_id` = `exmo2010_organization`.`monitoring_id`
"""

sql_complete_answers = """
SELECT
    COUNT(`exmo2010_qanswer`.`id`)
FROM `exmo2010_qanswer`
INNER JOIN `exmo2010_qquestion` ON (`exmo2010_qanswer`.`question_id` = `exmo2010_qquestion`.`id`)
INNER JOIN `exmo2010_questionnaire` ON (`exmo2010_qquestion`.`questionnaire_id` = `exmo2010_questionnaire`.`id`)
WHERE (
    `exmo2010_qanswer`.`task_id` = `exmo2010_task`.`id`
    AND `exmo2010_questionnaire`.`monitoring_id` = `exmo2010_organization`.`monitoring_id` )
"""

sql_complete_scores = """
SELECT
    COUNT(`exmo2010_score`.`id`)
FROM `exmo2010_score`
INNER JOIN `exmo2010_parameter` ON (`exmo2010_score`.`parameter_id` = `exmo2010_parameter`.`id`)
WHERE (
    `exmo2010_score`.`task_id` = `exmo2010_task`.`id`
    AND `exmo2010_score`.`revision` = 0
    AND NOT ((
        `exmo2010_score`.`parameter_id` IN (
            SELECT U2.`parameter_id`
            FROM `exmo2010_parameter_exclude` U2
            WHERE (U2.`organization_id` = `exmo2010_organization`.`id`  AND U2.`parameter_id` IS NOT NULL))
        AND `exmo2010_score`.`parameter_id` IS NOT NULL
        AND `exmo2010_parameter`.`id` IS NOT NULL)))
"""

sql_complete = """
    ((%(scores)s) + (%(answers)s)) * 100 /
    ((%(parameters)s) + (%(questions)s))
""" % {
    'scores': sql_complete_scores,
    'answers': sql_complete_answers,
    'parameters': sql_complete_parameters,
    'questions': sql_complete_questions,
}

# sql для приведение в абсолютные значения критериев
# если критерий оценки не релевантен, то возвращается -1
# если параметр не оценен или объекта Score не существует для данного параметра, то возвращается 0

# по формуле v1
sql_monitoring_v1 = """
(CASE exmo2010_parameter.complete
    WHEN 1 THEN
        (CASE exmo2010_score.complete
        WHEN 1 THEN 0.2
        WHEN 2 THEN 0.5
        WHEN 3 THEN 1
        ELSE 0
        END)
    ELSE -1
    END) as `complete`,
(CASE exmo2010_parameter.topical
    WHEN 1 THEN
        (CASE exmo2010_score.topical
        WHEN 1 THEN 0.7
        WHEN 2 THEN 0.85
        WHEN 3 THEN 1
        ELSE 0
        END)
    ELSE -1
    END) as `topical`,
(CASE exmo2010_parameter.accessible
    WHEN 1 THEN
        (CASE exmo2010_score.accessible
        WHEN 1 THEN 0.9
        WHEN 2 THEN 0.95
        WHEN 3 THEN 1
        ELSE 0
        END)
    ELSE -1
    END) as `accessible`,
(CASE exmo2010_parameter.hypertext
    WHEN 1 THEN
        (CASE exmo2010_parameter.document
            WHEN 1 THEN
                (CASE exmo2010_score.hypertext
                WHEN 0 THEN 0.2
                WHEN 1 THEN
                    (CASE exmo2010_score.document
                    WHEN 0 THEN 0.9
                    WHEN 1 THEN 1
                    ELSE 0
                    END)
                ELSE 0
                END)
            ELSE
                (CASE exmo2010_score.hypertext
                WHEN 0 THEN 0.2
                WHEN 1 THEN 1
                ELSE 0
                END)
            END)
    ELSE -1
    END) as `hypertext`
"""

# по формуле v8
sql_monitoring_v8 = """
(CASE exmo2010_parameter.complete
    WHEN 1 THEN
        (CASE exmo2010_score.complete
        WHEN 1 THEN 0.2
        WHEN 2 THEN 0.5
        WHEN 3 THEN 1
        ELSE 0
        END)
    ELSE -1
    END) as `complete`,
(CASE exmo2010_parameter.topical
    WHEN 1 THEN
        (CASE exmo2010_score.topical
        WHEN 1 THEN 0.7
        WHEN 2 THEN 0.85
        WHEN 3 THEN 1
        ELSE 0
        END)
    ELSE -1
    END) as `topical`,
(CASE exmo2010_parameter.accessible
    WHEN 1 THEN
        (CASE exmo2010_score.accessible
        WHEN 1 THEN 0.9
        WHEN 2 THEN 0.95
        WHEN 3 THEN 1
        ELSE 0
        END)
    ELSE -1
    END) as `accessible`,
(CASE exmo2010_parameter.hypertext
    WHEN 1 THEN
        (CASE exmo2010_score.hypertext
        WHEN 0 THEN 0.2
        WHEN 1 THEN 1
        ELSE 0
        END)
    ELSE -1
    END) as `hypertext`,
(CASE exmo2010_parameter.document
    WHEN 1 THEN
        (CASE exmo2010_score.document
        WHEN 0 THEN 0.85
        WHEN 1 THEN 1
        ELSE 0
        END)
    ELSE -1
    END) as `document`,
(CASE exmo2010_parameter.image
    WHEN 1 THEN
        (CASE exmo2010_score.image
        WHEN 0 THEN 0.95
        WHEN 1 THEN 1
        ELSE 0
        END)
    ELSE -1
    END) as `image`
"""

sql_monitoring_scores = """
SELECT
    `exmo2010_score`.`id`,
    `exmo2010_score`.`found`,
    `exmo2010_score`.`revision`,
    %(sql_monitoring)s,
    `exmo2010_parameter`.`weight`,
    `exmo2010_parameter`.`name` as parameter_name,
    COALESCE(%(sql_parameter_languages)s) as parameter_name,
    `exmo2010_parameter`.`id` as parameter_id,
    `exmo2010_organization`.`id` as organization_id,
    `exmo2010_organization`.`url`,
    `exmo2010_parameter`.`npa` as parameter_npa,
    COALESCE(%(sql_organization_languages)s) as organization_name,
    `exmo2010_task`.`status` as task_status,
    (%(sql_openness_initial)s) as openness_initial,
    (%(sql_openness)s) as task_openness
FROM `exmo2010_score`
INNER JOIN `exmo2010_task` ON (`exmo2010_score`.`task_id` = `exmo2010_task`.`id`)
INNER JOIN `exmo2010_organization` ON (`exmo2010_task`.`organization_id` = `exmo2010_organization`.`id`)
INNER JOIN `exmo2010_parameter` ON (`exmo2010_score`.`parameter_id` = `exmo2010_parameter`.`id`)
WHERE (
    `exmo2010_organization`.`monitoring_id` = %(monitoring_pk)s
    AND NOT ((
        `exmo2010_score`.`parameter_id` IN (
            SELECT U2.`parameter_id`
            FROM `exmo2010_parameter_exclude` U2
            WHERE (U2.`organization_id` = `exmo2010_organization`.`id`  AND U2.`parameter_id` IS NOT NULL))
        AND `exmo2010_score`.`parameter_id` IS NOT NULL
        AND `exmo2010_parameter`.`id` IS NOT NULL))
    )
ORDER BY task_openness DESC, organization_name ASC
"""


def iter_i18n_fields_sql(model, field_name):
    table = model._meta.db_table
    for lang in resolution_order(get_language()):
        yield "NULLIF(`%(table)s`.`%(field_name)s_%(lang)s`, '')" % locals()
