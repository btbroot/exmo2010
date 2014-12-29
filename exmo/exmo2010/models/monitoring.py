# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from core.sql import iter_i18n_fields_sql, sql_monitoring_scores
from .base import BaseModel
from .organization import Organization
from .parameter import Parameter
from .questionnaire import Questionnaire, QAnswer, QQuestion


PRE, RATE, RES, INT, FIN, PUB = 0, 1, 4, 3, 7, 5
MONITORING_PREPARE = 0
MONITORING_RATE = 1
MONITORING_RESULT = 4
MONITORING_INTERACTION = 3
MONITORING_FINALIZING = 7
MONITORING_PUBLISHED = 5
MONITORING_STATUS = (
    (MONITORING_PREPARE, _('prepare')),
    (MONITORING_RATE, _('initial evaluation')),
    (MONITORING_RESULT, _('results')),
    (MONITORING_INTERACTION, _('interact')),
    (MONITORING_FINALIZING, _('finishing')),
    (MONITORING_PUBLISHED, _('published')),
)

ANSWER_TIME_CHOICES = [(d, ungettext_lazy('%(count)d day', '%(count)d days', d) % {"count": d}) for d in range(1, 11)]


class Monitoring(BaseModel):
    class Meta(BaseModel.Meta):
        ordering = ('name',)

    name = models.CharField(max_length=255, verbose_name=_('name'))
    status = models.PositiveIntegerField(choices=MONITORING_STATUS, default=MONITORING_PREPARE, verbose_name=_('status'))
    hidden = models.BooleanField(default=False, verbose_name=_('Hide monitoring in statistics and ratings'))
    openness_expression = models.ForeignKey("OpennessExpression", default=8, verbose_name=_('Formula'))
    map_link = models.URLField(null=True, blank=True, verbose_name=_('Link to map'))

    # Максимальное время ответа в днях.
    time_to_answer = models.PositiveSmallIntegerField(choices=ANSWER_TIME_CHOICES, default=3,
                                                      verbose_name=_('Maximum time for answer'))
    no_interact = models.BooleanField(default=False, verbose_name=_('No interact stage'))

    rate_date = models.DateField(verbose_name=_('Monitoring evaluation begin date'))
    interact_date = models.DateField(verbose_name=_('Monitoring interact start date'))
    publish_date = models.DateField(verbose_name=_('Monitoring publish date'))
    finishing_date = models.DateField(verbose_name=_('Monitoring interact end date'))

    def __unicode__(self):
        return '%s' % self.name

    def has_questionnaire(self):
        return Questionnaire.objects.filter(monitoring=self).exists()

    def get_questionnaire(self):
        questionnaire = Questionnaire.objects.filter(monitoring=self)
        return questionnaire[0] if questionnaire else None

    def has_questions(self):
        return QQuestion.objects.filter(questionnaire__monitoring=self).exists()

    def ready_export_answers(self):
        """Готов ли мониторинг к экспорту ответов анкеты"""
        from .task import Task
        return QAnswer.objects.filter(question__questionnaire__monitoring=self,
                                      task__status=Task.TASK_APPROVED).exists()

    def rating(self, parameters=None, rating_type=None):
        """
        Calculate monitoring rating, annotate each approved task with openness and place in the resulting
         rating list
        Rerturns sorted tasks queryset
        Kwargs:
            rating_type (str): possible values are ['user', 'other', 'npa']

            parameters (QuerySet): parameters that will form calculated openness, used
             only if rating_type == 'user'

        """
        from .task import Task

        if rating_type == 'npa':
            parameters = self.parameter_set.filter(npa=True)
        elif rating_type == 'other':
            parameters = self.parameter_set.filter(npa=False)
        elif rating_type != 'user':
            parameters = None  # Use all parameters

        if not parameters and parameters is not None:
            # Parameters filter was given empty. Rating calculation is impossible.
            return []

        sql_openness = self.openness_expression.get_sql_openness(parameters)
        sql_openness_initial = self.openness_expression.get_sql_openness(parameters, initial=True)

        tasks = Task.approved_tasks.filter(organization__monitoring=self).extra(
            select={'task_openness': sql_openness, 'task_openness_initial': sql_openness_initial},
            where=['%s IS NOT NULL' % sql_openness],
            order_by=['-task_openness']).select_related('organization').distinct()

        previous_openness = None
        place = 0
        # NOTE: Tasks with equal openness SHOULD share same place!
        for task in tasks:
            if task.task_openness != previous_openness:
                previous_openness = task.task_openness
                place += 1
            task.place = place
            task.openness_delta = round(float(task.task_openness) - float(task.task_openness_initial), 3)

        return tasks

    def statistics(self):
        """
        Метод, возвращающий словарь со статистикой по мониторингу.

        """
        from .task import Task
        from .score import Score
        from .userprofile import UserProfile

        stat = {}
        scores = Score.objects.filter(task__organization__monitoring=self)

        stat['organization'] = self.organization_set.count()

        stat['organization_rated'] = Task.approved_tasks.filter(organization__monitoring=self).count()

        stat['organization_users'] = User.objects.filter(
            groups__name='organizations',
            userprofile__organization__in=self.organization_set.all()
        ).count()

        stat['organization_users_active'] = UserProfile.objects.filter(user__comment_comments__object_pk__in=scores)\
                                                               .distinct()\
                                                               .count()

        stat['expert'] = User.objects.filter(task__organization__monitoring=self).distinct().count()

        stat['comment_organization'] = Comment.objects.filter(
            content_type__model='score',
            object_pk__in=scores,
            user__in=User.objects.filter(groups__name='organizations')
        ).count()

        stat['comment_expert'] = Comment.objects.filter(
            content_type__model='score',
            object_pk__in=scores,
            user__in=User.objects.exclude(groups__name='organizations')
        ).count()

        rating_list = self.rating()
        if rating_list:
            stat['avg_openness'] = sum(t.task_openness for t in rating_list) / len(rating_list)
            stat['avg_openness_initial'] = sum(t.task_openness_initial for t in rating_list) / len(rating_list)
        else:
            stat.update(avg_openness=None, avg_openness_initial=None)
        return stat

    @property
    def has_npa(self):
        return self.parameter_set.filter(npa=True).exists()

    def sql_scores(self):
        sql_openness_initial = self.openness_expression.get_sql_openness(initial=True)
        sql_openness = self.openness_expression.get_sql_openness()
        sql_organization_languages = ', '.join(iter_i18n_fields_sql(Organization, 'name'))
        sql_parameter_languages = ', '.join(iter_i18n_fields_sql(Parameter, 'name'))

        result = sql_monitoring_scores % {
            'sql_monitoring': self.openness_expression.sql_monitoring(),
            'sql_openness_initial': sql_openness_initial,
            'sql_openness': sql_openness,
            'sql_organization_languages': sql_organization_languages,
            'sql_parameter_languages': sql_parameter_languages,
            'monitoring_pk': self.pk,
        }

        return result

    after_interaction_status = [MONITORING_INTERACTION, MONITORING_FINALIZING, MONITORING_PUBLISHED]

    is_prepare = property(lambda self: self.status == MONITORING_PREPARE)
    is_rate = property(lambda self: self.status == MONITORING_RATE)
    is_interact = property(lambda self: self.status == MONITORING_INTERACTION)
    is_finishing = property(lambda self: self.status == MONITORING_FINALIZING)
    is_published = property(lambda self: self.status == MONITORING_PUBLISHED)
