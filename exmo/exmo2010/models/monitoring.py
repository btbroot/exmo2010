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

from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.aggregates import Count
from django.utils.translation import ugettext as _

from core.sql import sql_monitoring_scores
from .base import BaseModel
from .questionnaire import Questionnaire, QAnswer


"""
Кол-во организаций
Кол-во оцененных организций (одобренных)
Кол-во зарегистрированных представителей для организаций
Кол-во активных представителей
Кол-во экспертов занятых в оценке
Кол-во комментариев оставленных представителями
Кол-во комментариев оставленных экспертами
Ср. знач. Кид
Ср. знач. первичного Кид
"""
MONITORING_STAT_DICT = {
    'organization': 0,
    'organization_rated': 0,
    'organization_users': 0,
    'organization_users_active': 0,
    'expert': 0,
    'comment_organization': 0,
    'comment_expert': 0,
    'avg_openness': 0,
    'avg_openness_initial': 0,
}


MONITORING_PREPARE = 0
MONITORING_RATE = 1
MONITORING_REVISION = 2
MONITORING_INTERACTION = 3
MONITORING_RESULT = 4
MONITORING_PUBLISHED = 5
MONITORING_FINALIZING = 7
MONITORING_STATUS = (
    (MONITORING_PREPARE, _('prepare')),
    (MONITORING_RATE, _('initial rate')),
    (MONITORING_RESULT, _('result')),
    (MONITORING_INTERACTION, _('interact')),
    (MONITORING_FINALIZING, _('finishing')),
    (MONITORING_PUBLISHED, _('published')),
)


class Monitoring(BaseModel):
    class Meta(BaseModel.Meta):
        ordering = ('name',)

    MONITORING_STATUS_NEW = ((MONITORING_PREPARE, _('prepare')),)

    MONITORING_EDIT_STATUSES = {
        MONITORING_RATE: _('Monitoring rate begin date'),
        MONITORING_INTERACTION: _('Monitoring interact start date'),
        MONITORING_FINALIZING: _('Monitoring interact end date'),
        MONITORING_PUBLISHED: _('Monitoring publish date'),
    }

    name = models.CharField(max_length=255, default="-", verbose_name=_('name'))
    status = models.PositiveIntegerField(
        choices=MONITORING_STATUS,
        default=MONITORING_PREPARE,
        verbose_name=_('status')
    )
    openness_expression = models.ForeignKey("OpennessExpression", default=8, verbose_name=_('openness expression'))
    map_link = models.URLField(
        null=True,
        blank=True,
        verbose_name=_('Link to map')
    )
    # Максимальное время ответа в днях.
    time_to_answer = models.PositiveSmallIntegerField(
        default=3,
        verbose_name=_('Maximum time to answer'))
    no_interact = models.BooleanField(
        default=False,
        verbose_name=_('No interact stage')
    )
    hidden = models.BooleanField(
        default=False,
        verbose_name=_('Hidden monitoring')
    )
    prepare_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('prepare date'),
    )
    rate_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Monitoring rate begin date'),
    )
    interact_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Monitoring interact start date'),
    )
    result_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('result date'),
    )
    publish_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Monitoring publish date'),
    )
    finishing_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Monitoring interact end date'),
    )

    def __unicode__(self):
        return '%s' % self.name

    @models.permalink
    def get_absolute_url(self):
        return ('exmo2010:tasks_by_monitoring', [str(self.id)])

    def _get_prepare(self):
        return self.status == MONITORING_PREPARE

    def _get_rate(self):
        return self.status == MONITORING_RATE

    def _get_interact(self):
        return self.status == MONITORING_INTERACTION

    def _get_result(self):
        return self.status == MONITORING_RESULT

    def _get_finishing(self):
        return self.status == MONITORING_FINALIZING

    def _get_published(self):
        return self.status == MONITORING_PUBLISHED

    def _get_active(self):
        return not self.is_prepare

    def has_questionnaire(self):
        return Questionnaire.objects.filter(monitoring=self).exists()

    def get_questionnaire(self):
        try:
            return Questionnaire.objects.get(monitoring=self)
        except ObjectDoesNotExist:
            return None

    def has_questions(self):
        questionnaire = self.get_questionnaire()
        if questionnaire and questionnaire.qquestion_set.exists():
            return True
        else:
            return False

    def del_questionnaire(self):
        try:
            questionnaire = Questionnaire.objects.get(monitoring=self)
        except ObjectDoesNotExist:
            pass
        else:
            questionnaire.delete()

    def ready_export_answers(self):
        '''
        Готов ли мониторинг к экспорту ответов анкеты
        '''
        from .task import Task
        questionnaire = self.get_questionnaire()
        if questionnaire and QAnswer.objects.filter(
           question__questionnaire=questionnaire, task__status=Task.TASK_APPROVED).exists():
            return True
        else:
            return False

    def statistics(self):
        """
        Метод, возвращающий словарь со статистикой по мониторингу.

        """
        from .task import Task
        from .score import Score
        from monitorings.views import rating

        stat = MONITORING_STAT_DICT
        stat['organization'] = self.organization_set.count()
        stat['organization_rated'] = Task.approved_tasks.filter(
            organization__monitoring=self
        ).count()
        stat['organization_users'] = User.objects.filter(
            groups__name='organizations',
            userprofile__organization__in=self.organization_set.all()
        ).count()
        stat['organization_users_active'] = MonitoringInteractActivity.\
            objects.filter(monitoring=self,).count()
        stat['expert'] = Task.objects.filter(
            organization__monitoring=self
        ).aggregate(count=Count('user', distinct=True))['count']
        stat['comment_organization'] = Comment.objects.filter(
            content_type__model='score',
            object_pk__in=Score.objects.filter(task__organization__monitoring=self),
            user__in=User.objects.filter(groups__name='organizations')
        ).count()

        stat['comment_expert'] = Comment.objects.filter(
            content_type__model='score',
            object_pk__in=Score.objects.filter(
                task__organization__monitoring=self),
            user__in=User.objects.exclude(groups__name='organizations')
        ).count()

        rating_list, avg = rating(self)
        stat['avg_openness'] = avg['openness']
        stat['avg_openness_initial'] = avg['openness_initial']
        return stat

    @property
    def has_npa(self):
        return self.parameter_set.filter(npa=True).exists()

    def sql_scores(self):
        sql_openness_initial = self.openness_expression.get_sql_openness(initial=True)
        sql_openness = self.openness_expression.get_sql_openness()

        result = sql_monitoring_scores % {
            'sql_monitoring': self.openness_expression.sql_monitoring(),
            'sql_openness_initial': sql_openness_initial,
            'sql_openness': sql_openness,
            'monitoring_pk': self.pk,
        }

        return result

    after_interaction_status = [MONITORING_INTERACTION, MONITORING_FINALIZING, MONITORING_PUBLISHED]

    is_prepare = property(_get_prepare)
    is_rate = property(_get_rate)
    is_interact = property(_get_interact)
    is_result = property(_get_result)
    is_finishing = property(_get_finishing)
    is_published = property(_get_published)
    is_active = property(_get_active)



class MonitoringInteractActivity(BaseModel):
    """
    Модель регистрации посещений мониторинга
    """
    class Meta(BaseModel.Meta):
        unique_together = ('user', 'monitoring')

    monitoring = models.ForeignKey(Monitoring)
    user = models.ForeignKey(User)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.user.userprofile.legal_name,
                             self.monitoring.name)