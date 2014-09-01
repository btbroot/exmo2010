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
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _

from .base import BaseModel
from .monitoring import MONITORING_STATUS, MONITORING_PREPARE
from .organization import Organization
from .parameter import Parameter
from .questionnaire import QQuestion, QAnswer
from .score import Score


class ApprovedTaskManager(models.Manager):
    """
    Менеджер для получения одобренных задач
    """
    def get_query_set(self):
        return super(ApprovedTaskManager, self).get_query_set().filter(status=Task.TASK_APPROVED)


class Task(BaseModel):
    class Meta(BaseModel.Meta):
        unique_together = (('user', 'organization'),)
        ordering = ('organization__name', 'user__username')
        permissions = (("view_task", "Can view task"),)

    TASK_OPEN = 0
    TASK_READY = TASK_CLOSE = TASK_CLOSED = 1
    TASK_APPROVED = TASK_APPROVE = 2
    TASK_CHECK = TASK_CHECKED = 3
    TASK_STATUS = (
        (TASK_OPEN, _('opened')),
        (TASK_CLOSE, _('closed')),
        (TASK_APPROVE, _('approved'))
    )

    # Assigned user. Choices should be soft-limited to active experts (limit in the task edit form).
    # It is ok to have tasks with assigned non-expert or inactive user in DB, since user may
    # experience change of its activity status or groups after assignment.
    user = models.ForeignKey(User, verbose_name=_('user'))

    organization = models.ForeignKey(Organization, verbose_name=_('organization'))
    status = models.PositiveIntegerField(choices=TASK_STATUS, default=TASK_OPEN, verbose_name=_('status'))

    def relevant_scores(self):
        return self.score_set.filter(revision=Score.REVISION_DEFAULT).exclude(parameter__exclude=self.organization)

    @property
    def openness_initial(self):
        return self.get_openness(initial=True)

    @property
    def openness(self):
        return self.get_openness()

    def get_openness(self, parameters=None, initial=False):
        sql_openness = self.organization.monitoring.openness_expression.get_sql_openness(parameters, initial)
        result = Task.objects.filter(pk=self.pk)\
                             .extra(select={'__openness': sql_openness})\
                             .values_list('__openness', flat=True)[0]

        return result

    @property
    def openness_npa(self):
        params = self.organization.monitoring.parameter_set.filter(npa=True)
        if params.exists():
            return self.get_openness(params)
        else:
            return 0

    @property
    def openness_other(self):
        params = self.organization.monitoring.parameter_set.filter(npa=False)
        if params.exists():
            return self.get_openness(params)
        else:
            return 0

    objects = models.Manager()  # The default manager.
    approved_tasks = ApprovedTaskManager()

    def __unicode__(self):
        return '%s: %s' % (self.user.username, self.organization.name)

    def save(self, *args, **kwargs):
        new_user_assigned = False
        if self.pk is None:
            new_user_assigned = True
        else:
            task = Task.objects.get(pk=self.pk)
            if task.user != self.user:
                new_user_assigned = True

        super(Task, self).save(*args, **kwargs)
        if new_user_assigned:
            from .. import mail
            mail.mail_task_assigned(self)
            TaskHistory.objects.create(task=self, user=self.user, status=self.organization.monitoring.status)

    _get_open = lambda self: self.status == self.TASK_OPEN
    _get_ready = lambda self: self.status == self.TASK_READY
    _get_approved = lambda self: self.status == self.TASK_APPROVED

    def _set_open(self, val):
        if val:
            self.status = self.TASK_OPEN
            self.full_clean()
            self.save()

    def _set_ready(self, val):
        if val:
            self.status = self.TASK_READY
            self.full_clean()
            self.save()

    def _set_approved(self, val):
        if val:
            self.status = self.TASK_APPROVED
            self.full_clean()
            self.save()

    @property
    def completeness(self):
        monitoring = self.organization.monitoring
        parameters_num = Parameter.objects.filter(monitoring=monitoring).exclude(exclude=self.organization).count()
        if parameters_num:
            questions_num = QQuestion.objects.filter(questionnaire__monitoring=monitoring).count()
            answers_num = QAnswer.objects.filter(question__questionnaire__monitoring=monitoring, task=self).count()
            scores_num = Score.objects.filter(task=self, parameter__monitoring=monitoring)\
                                      .filter(revision=Score.REVISION_DEFAULT, accomplished=True)\
                                      .exclude(parameter__exclude=self.organization).count()
            completeness = (scores_num + answers_num) * 100.0 / (parameters_num + questions_num)
        else:
            completeness = 0

        return completeness

    def get_rating_place(self, parameters=None):
        """
        Если задача в рейтинге (одобрена), то вернет место в
        рейтинге относительно прочих задач

        """
        task_places = {t.pk: t.place for t in self.organization.monitoring.rating(parameters)}
        return task_places.get(self.pk)

    @property
    def rating_place(self):
        return self.get_rating_place()

    @property
    def rating_place_npa(self):
        params = self.organization.monitoring.parameter_set.filter(npa=True)
        if params.exists():
            return self.get_rating_place(params)
        else:
            return None

    @property
    def rating_place_other(self):
        params = self.organization.monitoring.parameter_set.filter(npa=False)
        if params.exists():
            return self.get_rating_place(params)
        else:
            return None

    open = property(_get_open, _set_open)
    ready = property(_get_ready, _set_ready)
    approved = property(_get_approved, _set_approved)

    def clean(self):
        self.validate_for_state(self.status)

    def validate_for_state(self, status):
        """
        Не давать закрыть задачу если она не 100% выполнена
        Не давать закрыть задачу если уже есть одобренная
         задача для этой организации в мониторинге
        """
        if status in [self.TASK_READY, self.TASK_APPROVED]:
            if self.completeness != 100:
                raise ValidationError(ugettext('Ready task must be 100 percent complete.'))
        if status == self.TASK_APPROVED:
            approved = Task.approved_tasks.filter(organization=self.organization)
            if approved and self not in approved:
                raise ValidationError(
                    ugettext('Approved task for monitoring %(monitoring)s and organization %(organization)s '
                             'already exist.') % {'monitoring': self.organization.monitoring,
                                                  'organization': self.organization}
                )

    transitions = ['close_task', 'open_task', 'approve_task']
    state_transitions = {
        TASK_OPEN: [('close_task', TASK_READY)],
        TASK_APPROVED: [('open_task', TASK_OPEN)],
        TASK_READY: [('approve_task', TASK_APPROVED), ('open_task', TASK_OPEN)]
    }

    def current_transitions(self, validate=False):
        for action, next_state in self.state_transitions[self.status]:
            if validate:
                try:
                    self.check_state(next_state)
                except ValidationError:
                    continue
            yield action, next_state


class TaskHistory(BaseModel):
    """
    History of monitoring task.

    """
    task = models.ForeignKey(Task, verbose_name=_('task'))
    user = models.ForeignKey(User, verbose_name=_('user'))
    status = models.PositiveSmallIntegerField(
        choices=MONITORING_STATUS,
        default=MONITORING_PREPARE,
        verbose_name=_('status')
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('time'))

    class Meta(BaseModel.Meta):
        ordering = (
            'timestamp',
        )
