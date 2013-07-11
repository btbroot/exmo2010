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
import datetime
import string
import random
import re

from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models, IntegrityError
from django.db.models import Q
from django.db.models.aggregates import Count
from django.utils.translation import ugettext as _
from south.modelsinspector import add_introspection_rules
from tagging.models import Tag

from core.fields import TagField
from core.sql import *
from core.utils import clean_message
from exmo import config


# Типы вопросов анкеты. Добавить переводы!
QUESTION_TYPE_CHOICES = (
    (0, _("Text")),
    (1, _("Number")),
    (2, _("Choose a variant")),
)

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
    'avg_openness_first': 0,
}

INV_CODE_CHARS = string.ascii_uppercase + string.digits

INV_STATUS = [
    ('NTS', _('Not sent')),
    ('SNT', _('Sent')),
    ('RD', _('Read')),
    ('RGS', _('Registered')),
    ('ACT', _('Activated')),
]

INV_STATUS_ALL = [('ALL', _('All invitations'))] + INV_STATUS

MONITORING_PREPARE = 0
MONITORING_RATE = 1
MONITORING_REVISION = 2
MONITORING_INTERACT = 3
MONITORING_RESULT = 4
MONITORING_PUBLISH = 5
MONITORING_FINISHING = 7
MONITORING_STATUS = (
    (MONITORING_PREPARE, _('prepare')),
    (MONITORING_RATE, _('initial rate')),
    (MONITORING_RESULT, _('result')),
    (MONITORING_INTERACT, _('interact')),
    (MONITORING_FINISHING, _('finishing')),
    (MONITORING_PUBLISH, _('published')),
)


def generate_inv_code(ch_nr):
    """Генерит код приглашения с указанным количеством символов."""
    return "".join(random.sample(INV_CODE_CHARS, ch_nr))


class OpennessExpression(models.Model):
    """
    Модель для хранения кода и наименования формул расчета Кид
    """
    code    = models.PositiveIntegerField(primary_key=True)
    name    = models.CharField(max_length = 255, default = "-", verbose_name=_('name'))

    def __unicode__(self):
        return _('%(name)s (from EXMO2010 v%(code)d)') % { 'name': self.name, 'code': self.code }


class Monitoring(models.Model):

    MONITORING_STATUS_NEW = ((MONITORING_PREPARE, _('prepare')),)

    MONITORING_EDIT_STATUSES = {
        MONITORING_RATE: _('Monitoring rate begin date'),
        MONITORING_INTERACT: _('Monitoring interact start date'),
        MONITORING_FINISHING: _('Monitoring interact end date'),
        MONITORING_PUBLISH: _('Monitoring publish date'),
    }

    name = models.CharField(
        max_length=255,
        default="-",
        verbose_name=_('name'))
    status = models.PositiveIntegerField(
        choices=MONITORING_STATUS,
        default=MONITORING_PREPARE,
        verbose_name=_('status')
    )
    openness_expression = models.ForeignKey(OpennessExpression,
                                            default=8, verbose_name=_('openness expression'))
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
        return self.status == MONITORING_INTERACT

    def _get_result(self):
        return self.status == MONITORING_RESULT

    def _get_finishing(self):
        return self.status == MONITORING_FINISHING

    def _get_published(self):
        return self.status == MONITORING_PUBLISH

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
            questionnaire =  Questionnaire.objects.get(monitoring=self)
        except ObjectDoesNotExist:
            pass
        else:
            questionnaire.delete()


    def ready_export_answers(self):
        #Готов ли мониторинг к экспорту ответов анкеты
        questionnaire = self.get_questionnaire()
        if questionnaire and QAnswer.objects.filter(
            question__questionnaire=questionnaire,
            task__status=Task.TASK_APPROVED).exists():
            return True
        else:
            return False

    def statistics(self):
        """
        Метод, возвращающий словарь со статистикой по мониторингу.
        """
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
            object_pk__in=Score.objects.filter(
                task__organization__monitoring=self),
            user__in = User.objects.filter(groups__name='organizations'),
        ).count()

        stat['comment_expert'] = Comment.objects.filter(
            content_type__model='score',
            object_pk__in=Score.objects.filter(
                task__organization__monitoring=self),
            user__in=User.objects.exclude(groups__name='organizations')
        ).count()
        from core.helpers import rating
        rating_list, avg = rating(self)
        stat['avg_openness'] = avg['openness']
        stat['avg_openness_first'] = avg['openness_first']
        return stat

    @property
    def has_npa(self):
        return self.parameter_set.filter(npa=True).exists()

    after_interaction_status = [MONITORING_INTERACT, MONITORING_FINISHING,
                                MONITORING_PUBLISH]

    is_prepare = property(_get_prepare)
    is_rate = property(_get_rate)
    is_interact = property(_get_interact)
    is_result = property(_get_result)
    is_finishing = property(_get_finishing)
    is_published = property(_get_published)
    is_active = property(_get_active)

    class Meta:
        ordering = ('name',)


class Questionnaire(models.Model):
    """Анкета, привязанная к мониторингу"""
    monitoring = models.ForeignKey(Monitoring, verbose_name=_("Monitoring"),
                                   unique=True)
    title = models.CharField(max_length=300, verbose_name=_("Questionnaire name"),
        blank=True)
    comment = models.CharField(max_length=600, verbose_name=_("Questionnaire comment"),
        blank=True)

    def __unicode__(self):
        return '%s' % self.monitoring.__unicode__()


class QQuestion(models.Model):
    """Вопрос анкеты, привязанной к мониторингу"""
    questionnaire = models.ForeignKey(Questionnaire,
        verbose_name=_("Questionnaire"))
    qtype = models.PositiveSmallIntegerField(choices=QUESTION_TYPE_CHOICES,
                                             verbose_name=_("Question type"))
    question = models.CharField(_("Question"), max_length=300)
    comment = models.CharField(_("Question comment"), max_length=600,
        blank=True)

    def __unicode__(self):
        return '%s: %s' % (self.questionnaire.__unicode__(), self.question)


class AnswerVariant(models.Model):
    """Вариант ответа на вопрос анкеты, предполагающий варианты"""
    qquestion = models.ForeignKey(QQuestion, verbose_name=_("Question"))
    answer = models.CharField(_("Answer"), max_length=300)

    def __unicode__(self):
        return self.answer


class OrganizationMngr(models.Manager):
    """
    Менеджер с одним специальным методом для генерации кодов приглашения
     для всех орг-ий, у которых его нет.
    """
    def create_inv_codes(self):
        orgs = self.filter(inv_code="")
        for o in orgs:
            o.inv_code = generate_inv_code(6)
            o.save()


phone_re = re.compile(r'([+])?([\d()\s\-]+)[-\.\s]?(\d{2})[-\.\s]?(\d{2})')
phone_re_reverse = re.compile(r'(\d{2})[-\.\s]?(\d{2})[-\.\s]?([\d()\s\-]+)([+])?')
email_re = re.compile(r'([0-9a-zA-Z]([-\.\w]*[0-9a-zA-Z])*@([0-9a-zA-Z][-\w]*[0-9a-zA-Z]\.)+[a-zA-Z]{2,9})')
delimiters_re = re.compile(r',|\s||(,\s)|\n|(,\n)')


class EmailsField(models.TextField):
    def to_python(self, value):
        sub_emails = re.sub(email_re, '', value)
        sub_emails = re.sub(delimiters_re, '', sub_emails)
        if sub_emails:
            raise ValidationError(_('Illegal symbols in email field.'))
        emails = re.findall(email_re, value)
        addresses = ""
        for e in emails:
            email = e[0] + ", "
            addresses += email
        return addresses.rstrip(", ")

add_introspection_rules([], ["^exmo2010\.models\.EmailsField"])


class PhonesField(models.TextField):
    def to_python(self, value):
        sub_phones = re.sub(phone_re, '', value)
        sub_phones = re.sub(delimiters_re, '', sub_phones)
        if sub_phones:
            raise ValidationError(_('Illegal symbols in phone field.'))
        phones = re.split(r',|\n', value)
        numbers = ""
        for p in phones:
            p = p.rstrip()
            p = p.lstrip()
            if " " in p or "-" in p:
                number = p
            else:
                ntmp = re.findall(phone_re_reverse, p[::-1])[0]
                number = ntmp[3][::-1] + ntmp[2][::-1] + "-" + ntmp[1][::-1] + "-" + ntmp[0][::-1]

            number += ", "
            numbers += number
        return numbers.rstrip(", ")

add_introspection_rules([], ["^exmo2010\.models\.PhonesField"])


class Organization(models.Model):
    """ Fields:
    name -- Unique organization name
    url -- Internet site URL
    email -- list of emails
    phone -- list of phones
    keywords -- Keywords for autocomplete and search (not used)
    comments -- Additional comment (not used)

    """
    name = models.CharField(max_length=255, verbose_name=_('name'))
    url = models.URLField(max_length=255, null=True, blank=True, verify_exists=False, verbose_name=_('url'))
    keywords = TagField(null=True, blank=True, verbose_name=_('keywords'))
    email = EmailsField(null=True, blank=True, verbose_name=_('email'))
    phone = PhonesField(null=True, blank=True, verbose_name=_('phone'))
    comments = models.TextField(null=True, blank=True, verbose_name=_('comments'))
    monitoring = models.ForeignKey(Monitoring, verbose_name=_('monitoring'))
    inv_code = models.CharField(verbose_name=_("Invitation code"), blank=True, max_length=6, unique=True)
    inv_status = models.CharField(max_length=3,
                                  choices=INV_STATUS, default='NTS',
                                  verbose_name=_('Invitation status'))

    objects = OrganizationMngr()

    def save(self, *args, **kwargs):
        if not self.pk and not self.inv_code:
            self.inv_code = generate_inv_code(6)
        super(Organization, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

    def _get_tags(self):
        return Tag.objects.get_for_object(self)

    def _set_tags(self, tag_list):
        Tag.objects.update_tags(self, tag_list)

    tags = property(_get_tags, _set_tags)

    class Meta:
        ordering = ('name',)
        unique_together = (
            ('name', 'monitoring'),
        )


class InviteOrgs(models.Model):
    """
    Invites organizations history.

    """
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('date and time'))
    monitoring = models.ForeignKey(Monitoring, verbose_name=_('monitoring'))
    comment = models.TextField(verbose_name=_('comment'))
    inv_status = models.CharField(max_length=3,
                                  choices=INV_STATUS_ALL, default='ALL',
                                  verbose_name=_('Invitation status'))


class EmailTasks(models.Model):
    """
    Model with tasks ids for each organization (used by celery).

    """
    organization = models.ForeignKey(Organization, verbose_name=_('organization'))
    task_id = models.CharField(max_length=60, verbose_name=_('task id'), db_index=True)


class Parameter(models.Model):
    """Параметр."""
    code = models.PositiveIntegerField(verbose_name=_('code'))
    name = models.CharField(max_length=1000, verbose_name=_('name'),
        db_index=False)
    description = models.TextField(blank=True, verbose_name=_('description'))
    monitoring = models.ForeignKey(Monitoring, verbose_name=_('monitoring'))
    exclude = models.ManyToManyField(Organization, null=True, blank=True,
        verbose_name=_('excluded organizations'))
    weight = models.IntegerField(verbose_name=_('weight'))
    keywords = TagField(blank=True, verbose_name=_('keywords'))
    complete = models.BooleanField(default=True, verbose_name=_('complete'))
    topical = models.BooleanField(default=True, verbose_name=_('topical'))
    accessible = models.BooleanField(default=True,
        verbose_name=_('accessible'))
    hypertext = models.BooleanField(default=True, verbose_name=_('hypertext'))
    document = models.BooleanField(default=True, verbose_name=_('document'))
    image = models.BooleanField(default=True, verbose_name=_('image'))
    npa = models.BooleanField(default=False, verbose_name=_('coherent'))

#I dont know why, but this breaks reversion while import-(
    def __unicode__(self):
        return self.name

    def _get_tags(self):
        return Tag.objects.get_for_object(self)

    def _set_tags(self, tag_list):
        Tag.objects.update_tags(self, tag_list)

    tags = property(_get_tags, _set_tags)

    class Meta:
        ordering = ('code','name',)
        unique_together = (
            ('code', 'monitoring'),
            ('name', 'monitoring'),
        )



class OpenTaskManager(models.Manager):
    """
    Менеджер для получения открытых задач
    """
    def get_query_set(self):
        return super(OpenTaskManager, self).get_query_set().filter(status = Task.TASK_OPEN)



class ReadyTaskManager(models.Manager):
    """
    Менеджер для получения закрытых задач
    """
    def get_query_set(self):
        return super(ReadyTaskManager, self).get_query_set().filter(status = Task.TASK_READY)


class ApprovedTaskManager(models.Manager):
    """
    Менеджер для получения одобренных задач
    """
    def get_query_set(self):
        return super(ApprovedTaskManager, self).get_query_set().filter(status = Task.TASK_APPROVED)


class Task(models.Model):
    TASK_OPEN = 0
    TASK_READY = TASK_CLOSE = TASK_CLOSED = 1
    TASK_APPROVED = TASK_APPROVE = 2
    TASK_CHECK = TASK_CHECKED = 3
    TASK_STATUS = (
        (TASK_OPEN, _('opened')),
        (TASK_CLOSE, _('closed')),
        (TASK_APPROVE, _('approved'))
    )
    user = models.ForeignKey(User, verbose_name=_('user'))
    organization = models.ForeignKey(Organization, verbose_name=_('organization'))
    status = models.PositiveIntegerField(
        choices=TASK_STATUS,
        default=TASK_OPEN,
        verbose_name=_('status'),
    )

    #хранит рассчитанное значение первичного Кид. обновляется по сигналу
    openness_first = models.FloatField(
        default=-1,
        editable=False,
        verbose_name=_('openness first'),
    )

    def _sql_openness(self, parameters=None):
        """
        функция для получения SQL пригодного для использования в extra(select=
        по умолчанию считается для всех параметров
        если указать parameters, то считается только для параметров имеющих соотв. pk
        """
        sql_score_openness = sql_score_openness_v8
        #empty addtional filter for parameter
        sql_parameter_filter = ""
        if self.organization.monitoring.openness_expression.code == 1:
            sql_score_openness = sql_score_openness_v1
        if parameters:
            if isinstance(parameters[0], Parameter):
                parameters_pk_list = [p.pk for p in parameters]
            else:
                parameters_pk_list = parameters
            sql_parameter_filter = "AND `exmo2010_parameter`.`id` in (%s)" %\
                               ",".join([str(p) for p in parameters_pk_list])
        return sql_task_openness % {
            'sql_score_openness': sql_score_openness,
            'sql_parameter_filter': sql_parameter_filter,
        }

    def get_openness(self, parameters=None):
        return Task.objects.filter(
            pk=self.pk
        ).extra(select={
            '__openness': self._sql_openness(parameters)
        }).values('__openness')[0]['__openness'] or 0

    @property
    def openness(self):
        return self.get_openness()

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

    def update_openness(self):
        #по умолчанию openness_first=-1.
        #проверять на 0 нельзя, т.к. возможно что до взаимодействия openness=0
        if self.organization.monitoring.is_interact and self.openness_first < 0:
            self.openness_first = self.openness
            self.save()

# want to hide TASK_OPEN, TASK_READY, TASK_APPROVED -- set initial quesryset with filter by special manager
# sa http://docs.djangoproject.com/en/1.2/topics/db/managers/#modifying-initial-manager-querysets

    objects = models.Manager() # The default manager.
    open_tasks = OpenTaskManager()
    ready_tasks = ReadyTaskManager()
    approved_tasks = ApprovedTaskManager()

    def __unicode__(self):
        return '%s: %s' % (self.user.username, self.organization.name)

    class Meta:
        unique_together = (
            ('user', 'organization'),
        )
        ordering = ('organization__name', 'user__username')
        permissions = (("view_task", "Can view task"),)

    def clean(self):
        """
        Не давать закрыть задачу если она не 100% выполнена
        Не давать закрыть задачу если уже есть одобренная
         задача для этой организации в мониторинге
        """
        if self.ready or self.approved:
            if self.complete != 100:
                raise ValidationError(_('Ready task must be 100 percent complete.'))
        if self.approved:
            if Task.approved_tasks.filter(organization = self.organization).count() != 0 and \
               self not in Task.approved_tasks.filter(organization = self.organization):
                raise ValidationError(_('Approved task for monitoring %(monitoring)s and organization %(organization)s already exist.') % {
                    'monitoring': self.organization.monitoring,
                    'organization': self.organization,
                })

    def save(self, *args, **kwargs):
        if self.pk is not None:
            task = Task.objects.get(pk=self.pk)
            if task.user != self.user:
                task_user_changed.send(sender=self)
        super(Task, self).save(*args, **kwargs)

    def _get_open(self):
        if self.status == self.TASK_OPEN: return True
        else: return False

    def _get_ready(self):
        if self.status == self.TASK_READY: return True
        else: return False

    def _get_approved(self):
        if self.status == self.TASK_APPROVED: return True
        else: return False

    def _set_open(self, val):
        if val:
            self.status = self.TASK_OPEN
            self.full_clean()
            self.save()

    def _set_ready(self ,val):
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
    def complete(self):
        """
        Расчёт выполненности
        """
        complete = 0
        parameters_num = Parameter.objects.filter(monitoring=self.organization.monitoring).exclude(exclude=self.organization).count()
        questions_num = QQuestion.objects.filter(questionnaire__monitoring=self.organization.monitoring).count()
        answers_num = QAnswer.objects.filter(question__questionnaire__monitoring= self.organization.monitoring, task=self).count()
        if parameters_num:
            scores_num = Score.objects.filter(
                task=self,
                revision=Score.REVISION_DEFAULT,
                ).exclude(
                    parameter__exclude=self.organization
                    ).count()
            complete = (scores_num + answers_num) * 100.0 / (parameters_num + questions_num)
        return complete

    def get_rating_place(self, parameters=None):
        """
        Если задача в рейтинге (одобрена), то вернет место в
        рейтинге относительно прочих задач
        """
        from core.helpers import rating
        place = None
        rating_list, avg = rating(self.organization.monitoring, parameters)
        for rating_object in rating_list:
            if rating_object['task'] == self:
                place = rating_object['place']
                break
        return place

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

    def get_questionnaire_answers(self):
        return QAnswer.objects.filter(task=self).order_by("pk")

    def all_questionnaire_answered(self):
        """
        Метод, возвращающего False/True в зависимости от того,
        даны ли ответы на все вопросы анкеты или нет.
        """
        questionnaire = self.organization.monitoring.get_questionnaire()
        if questionnaire and questionnaire.qquestion_set.count()==QAnswer.\
        objects.filter(task=self).count():
            return True
        else:
            return False

    open = property(_get_open, _set_open)
    ready = property(_get_ready, _set_ready)
    approved = property(_get_approved, _set_approved)


class TaskHistory(models.Model):
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

    class Meta:
        ordering = (
            'timestamp',
        )


class QAnswer(models.Model):
    """Ответ на вопрос анкеты"""
    task = models.ForeignKey(Task)
    question = models.ForeignKey(QQuestion, verbose_name=_("Question"))
    text_answer = models.CharField(_("Text answer"), max_length=300,
        blank=True)
    numeral_answer = models.PositiveIntegerField(_("Numerical answer"),
        blank=True, null=True)
    variance_answer = models.ForeignKey(AnswerVariant,
        verbose_name=_("Variance choice"), blank=True, null=True)
    def answer(self, for_form=False):
        if self.question.qtype == 0:
            return self.text_answer
        elif self.question.qtype == 1:
            return self.numeral_answer
        elif self.question.qtype == 2:
            if self.variance_answer:
                if for_form:
                    return self.variance_answer
                else:
                    return self.variance_answer.answer
            else:
                return None
    class Meta:
        unique_together = ('task','question')

    def __unicode__(self):
        return '%s: %s' % (self.task.__unicode__(),
                           self.question.__unicode__())


class Score(models.Model):
    """
    Модель оценки
    """

    REVISION_DEFAULT = 0
    REVISION_INTERACT = 1

    REVISION_CHOICE = (
        (REVISION_DEFAULT, _('default revision')),
        (REVISION_INTERACT, _('interact revision')),
    )

    task = models.ForeignKey(
        Task,
        verbose_name=_('task'),
    )
    parameter = models.ForeignKey(
        Parameter,
        verbose_name=_('parameter'),
    )
    found = models.IntegerField(
        choices=((0, 0), (1, 1)),
        verbose_name=_('found'),
    )
    foundComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('foundComment'),
        )
    complete = models.IntegerField(
        null=True,
        blank=True,
        choices=((1, 1), (2, 2), (3, 3)),
        verbose_name=_('complete'),
    )
    completeComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('completeComment'),
    )
    topical = models.IntegerField(
        null=True,
        blank=True,
        choices=((1, 1), (2, 2), (3, 3)),
        verbose_name=_('topical'),
    )
    topicalComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('topicalComment'),
    )
    accessible = models.IntegerField(
        null=True,
        blank=True,
        choices=((1, 1), (2, 2), (3, 3)),
        verbose_name=_('accessible'),
    )
    accessibleComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('accessibleComment'),
    )
    hypertext = models.IntegerField(
        null=True,
        blank=True,
        choices=((0, 0), (1, 1)),
        verbose_name=_('hypertext'),
    )
    hypertextComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('hypertextComment'),
    )
    document = models.IntegerField(
        null=True,
        blank=True,
        choices=((0, 0), (1, 1)),
        verbose_name=_('document'),
    )
    documentComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('documentComment'),
    )
    image = models.IntegerField(
        null=True,
        blank=True,
        choices=((0, 0), (1, 1)),
        verbose_name=_('image'),
    )
    imageComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('imageComment'),
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Recomendations'),
    )
    created = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
    )
    edited = models.DateTimeField(
        null=True,
        blank=True,
        auto_now=True,
    )
    revision = models.PositiveIntegerField(
        default=REVISION_DEFAULT,
        choices=REVISION_CHOICE,
    )

    def __unicode__(self):
        return '%s: %s [%d]' % (
            self.task.user.username,
            self.task.organization.name,
            self.parameter.code
        )

    def clean(self):
        """
        Оценка не может быть заполнена частично
        В оценке не может быть оценено то,
        что не предусмотрено к оценке в параметре
        У оценки не может быть found=0 при не пустых прочих критериях
        """
        if self.found:
            if self.parameter.complete and self.complete in ('', None):
                raise ValidationError(_('Complete must be set'))
            if self.parameter.topical and self.topical in ('', None):
                raise ValidationError(_('Topical must be set'))
            if self.parameter.accessible and self.accessible in ('', None):
                raise ValidationError(_('Accessible must be set'))
            if self.parameter.hypertext  and self.hypertext  in ('', None):
                raise ValidationError(_('Hypertext must be set'))
            if self.parameter.document   and self.document   in ('', None):
                raise ValidationError(_('Document must be set'))
            if self.parameter.image      and self.image      in ('', None):
                raise ValidationError(_('Image must be set'))
        elif any((
            self.complete != None,
            self.topical != None,
            self.accessible != None,
            self.hypertext != None,
            self.document != None,
            self.image != None,
            self.completeComment,
            self.topicalComment,
            self.accessibleComment,
            self.hypertextComment,
            self.documentComment,
            self.imageComment,
            )):
            raise ValidationError(_('Not found, but some excessive data persists'))

    @models.permalink
    def get_absolute_url(self):
        return ('exmo2010:score_view', [str(self.id)])

    def _get_claim(self):
        return Claim.objects.filter(score=self, close_date__isnull=True, addressee=self.task.user).exists()

    def _get_openness(self):
        return openness_helper(self)

    def add_clarification(self, creator, comment):
        """
        Добавляет уточнение
        """
        comment = clean_message(comment)
        clarification = Clarification(score=self,
                                      creator=creator,
                                      comment=comment)
        clarification.save()
        return clarification

    def add_claim(self, creator, comment):
        comment = clean_message(comment)
        claim = Claim(score=self,
                      creator=creator,
                      comment=comment)
        claim.addressee=claim.score.task.user
        claim.full_clean()
        claim.save()
        return claim

    def claim_color(self):
        """
        Return the color of the claim`s icon.

        """
        color = None

        claims = Claim.objects.filter(score=self, addressee=self.task.user)
        open_claims = claims.filter(close_date__isnull=True)

        if claims:
            color = 'green'
            if open_claims:
                color = 'red'

        return color

    def create_revision(self, revision):
        """
        Создание ревизии оценки
        """
        if self.task.organization.monitoring.status in Monitoring.after_interaction_status \
           and revision == Score.REVISION_INTERACT:
            revision_score = Score.objects.filter(
                task=self.task,
                parameter=self.parameter,
                revision=revision,
            )
            if not revision_score and self.pk:
                revision_score = Score.objects.get(pk=self.pk)
                revision_score.pk = None
                revision_score.revision = revision
                revision_score.full_clean()
                revision_score.save()

    active_claim = property(_get_claim)
    openness = property(_get_openness)

    class Meta:
        unique_together = (
            ('task','parameter','revision'),
        )
        ordering = (
            'task__user__username',
            'task__organization__name',
            'parameter__code'
        )


class Claim(models.Model):
    """Модель претензий/замечаний"""
    score = models.ForeignKey(Score, verbose_name=_('score'))  # Оценка.
    # Дата создания.
    open_date = models.DateTimeField(auto_now_add=True,
                                     verbose_name=_('claim open'))
    # Дата закрытия. По её наличию определяется закрыта претензия или нет.
    close_date = models.DateTimeField(null=True, blank=True,
                                      verbose_name=_('claim close'))
    # Комментарий.
    comment = models.TextField(blank=True, verbose_name=_('comment'))

    # Ответ.
    answer = models.TextField(blank=True, verbose_name=_('comment'))

    # Кто закрыл претензию.
    close_user = models.ForeignKey(User, null=True, blank=True,
        verbose_name=_('user who close'), related_name='close_user')
    # Кто создал претензию.
    creator = models.ForeignKey(User, verbose_name=_('creator'),
                                related_name='creator')
    addressee = models.ForeignKey(User, default=1,
        verbose_name=_('addressee'), related_name='addressee')

    def add_answer(self, user, answer):
        self.answer = clean_message(answer)
        self.close_user = user
        self.close_date = datetime.datetime.now()
        self.save()
        return self

    def __unicode__(self):
        return _('claim for %(score)s from %(creator)s') %\
               {'score': self.score, 'creator': self.creator}

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для того, чтобы автоматически заполнять
        значение поля`addressee`, но только в момент первоначального создания
        экземпляра модели.
        """
        if not self.id:  # Экземпляр новый.
            self.addressee = self.score.task.user
        super(Claim, self).save(*args, **kwargs)

    class Meta:
        permissions = (("view_claim", "Can view claim"),)


class Clarification(models.Model):
    """
    Модель уточнений, по наличию даты закрытия определяется
    закрыто уточнение или нет.
    """
    score = models.ForeignKey(Score, verbose_name=_('score'))

    open_date = models.DateTimeField(auto_now_add=True,
                                     verbose_name=_('clarification open'))
    creator = models.ForeignKey(User,
                                verbose_name=_('creator'),
                                related_name='clarification_creator')

    comment = models.TextField(blank=True,
                               verbose_name=_('comment'))

    close_date = models.DateTimeField(null=True,
                                      blank=True,
                                      verbose_name=_('clarification close'))

    answer = models.TextField(blank=True, verbose_name=_('comment'))

    close_user = models.ForeignKey(User,
                                   null=True,
                                   blank=True,
                                   verbose_name=_('user who close'),
                                   related_name='clarification_close_user')

    def add_answer(self, user, answer):
        self.answer = clean_message(answer)
        self.close_user = user
        self.close_date = datetime.datetime.now()
        self.save()
        return self


    def __unicode__(self):
        return _('clarification for %(score)s from %(creator)s') % \
            {'score': self.score,
             'creator': self.creator}

    class Meta:
        permissions = (("view_clarification", "Can view clarification"),)

    @property
    def addressee(self):
        return self.score.task.user


def openness_helper(score):
    """
    Помощник для вычисления Кид через SQL
    """
    sql="""
    SELECT
    %(score_openness)s
    FROM
	exmo2010_score
	join exmo2010_parameter on exmo2010_score.parameter_id=exmo2010_parameter.id
	where exmo2010_score.id=%(pk)d
    """ % {
        'pk': score.pk,
        'score_openness': score.task._sql_openness(),
    }
    s = Score.objects.filter(pk=score.pk).extra(select={
        'sql_openness': sql,
    })
    return float(s[0].score_openness)

from digest_email.models import Digest, DigestPreference
from django.contrib.auth.models import Group
import json

SEX_CHOICES = (
    (0, _("not set")),
    (1, _("male")),
    (2, _("female")),
)


class ExtUPManager(models.Manager):
    """
    Выдает только внешних пользователей.
    """
    def get_query_set(self):
        return super(ExtUPManager, self).\
               get_query_set().\
               exclude(user__is_superuser=True).\
               exclude(user__is_staff=True).\
               exclude(user__groups__name__in=UserProfile.expert_groups).\
               distinct()


class IntUPManager(models.Manager):
    """
    Выдает только внутренних пользователей.
    """
    def get_query_set(self):
        return super(IntUPManager, self).\
               get_query_set().\
               filter(Q(user__is_superuser=True) |
                      Q(user__is_staff=True) |
                      Q(user__groups__name__in=UserProfile.expert_groups)).\
               distinct()


class UserProfile(models.Model):
    """
    Наша кастомная модель профиля пользователя.

    Notification types can be:
    0 - disable
    1 - one mail per one comment/change
    2 - digest

    Preference field
    this is like::
        {
            'notify_comment': {
                'self': False,
                'digest_duratation': 5,
                'type': 0
            },
            'notify_score': {
                'digest_duratation': 5,
                'type': 0
            },
        }
    type is one of notification types
    """
    # Оповещение отключено.
    NOTIFICATION_TYPE_DISABLE = 0
    # Оповещение включено. По одному письму на событие.
    NOTIFICATION_TYPE_ONEBYONE = 1
    # Оповещение включено. По одному письму в период времени. Оповещение дайджестами.
    NOTIFICATION_TYPE_DIGEST = 2

    NOTIFICATION_TYPE_CHOICES = (
        (NOTIFICATION_TYPE_DISABLE, _('disabled')),
        (NOTIFICATION_TYPE_ONEBYONE, _('one email per one comment/change')),
        (NOTIFICATION_TYPE_DIGEST, _('digest notification')),
    )

    objects = models.Manager()  # Все пользователи.
    externals = ExtUPManager()  # Только внешние.
    internals = IntUPManager()  # Только внутренние.

    user = models.ForeignKey(User, unique=True)
    organization = models.ManyToManyField(Organization, null=True, blank=True,
                                      verbose_name=_('organizations for view'))
    preference = models.TextField(blank=True, verbose_name=_('Preferences'))
    sex = models.PositiveSmallIntegerField(verbose_name=_("Sex"),
        choices=SEX_CHOICES, default=0, db_index=True)
    subscribe = models.BooleanField(
        verbose_name=_("Subscribe to news e-mail notification"), default=False)
    position = models.CharField(verbose_name=_("Seat"), max_length=48,
        blank=True)
    phone = models.CharField(verbose_name=_("Phone"), max_length=30,
        blank=True)

    @property
    def get_preference(self):
        try:
            return json.loads(self.preference)
        except (ValueError, TypeError):
            return {}

    def _get_notify_preference(self, preference):
        prefs = self.get_preference
        if prefs.has_key(preference):
            pref = prefs[preference]
        else:
            pref = {}
        if not pref.has_key('type'):
            pref['type'] = self.NOTIFICATION_TYPE_DISABLE
        else:
            pref['type'] = int(pref['type'])
        if not pref.has_key('self'):
            pref['self'] = False
        if pref.has_key('digest_duratation'):
            if pref['digest_duratation']:
                pref['digest_duratation'] = int(pref['digest_duratation'])
            else:
                pref['digest_duratation'] = 0
        else:
            pref['digest_duratation'] = 1
        return pref

    @property
    def notify_comment_preference(self):
        return self._get_notify_preference('notify_comment')

    @notify_comment_preference.setter
    def notify_comment_preference(self, pref):
        prefs = self.get_preference
        prefs['notify_comment'] = pref
        self.preference = json.dumps(prefs)

    @property
    def notify_score_preference(self):
        return self._get_notify_preference('notify_score')

    @notify_score_preference.setter
    def notify_score_preference(self, pref):
        prefs = self.get_preference
        prefs['notify_score'] = pref
        self.preference = json.dumps(prefs)

    def clean(self):
        super(UserProfile, self).clean()
        for notify in ['notify_score','notify_comment']:
            if self._get_notify_preference(notify)['type'] == self.NOTIFICATION_TYPE_DIGEST:
                if self._get_notify_preference(notify)['digest_duratation'] < 1:
                    raise ValidationError(_('Digest duratation must be greater or equal than 1.'))

    def save(self,*args,**kwargs):
        """
        Переопределение метода для сохранения настроек дайджеста.
        """
        super(UserProfile, self).save(*args, **kwargs)
        for notify in ['notify_score','notify_comment']:
            if self._get_notify_preference(notify)['type'] == self.NOTIFICATION_TYPE_DIGEST:
                # create DigestPreference.
                digest, created = Digest.objects.get_or_create(name=notify)
                dpref, created = DigestPreference.objects.get_or_create(user = self.user, digest = digest)
                dpref.interval = self._get_notify_preference(notify)['digest_duratation']
                dpref.full_clean()
                dpref.save()
            else:
                digest, created = Digest.objects.get_or_create(name = notify)
                DigestPreference.objects.filter(user = self.user, digest = digest).delete()

    def is_internal(self):
        """Внутренний пользователь или внешний."""
        try:
            UserProfile.externals.get(pk=self.pk)
        except ObjectDoesNotExist:
            return True
        else:
            return False

    def _is_expert(self):
        return self.user.groups.filter(name__in=self.expert_groups).exists() or self.user.is_superuser

    def _is_expertB(self):
        return self.user.groups.filter(name=self.expertB_group).exists() or self.user.is_superuser

    def _is_expertA(self):
        return self.user.groups.filter(name=self.expertA_group).exists() or self.user.is_superuser

    def _is_manager_expertB(self):
        return self.user.groups.filter(name=self.expertB_manager_group).exists() or self.user.is_superuser

    def _is_customer(self):
        return self.user.groups.filter(name=self.customer_group).exists() or self.user.is_superuser

    def _is_organization(self):
        return self.user.groups.filter(name=self.organization_group).exists() or self.user.is_superuser

    @property
    def bubble_info(self):
        """
        Определяем наличие связанных организаций в мониторингах с определенными
        статусами для показа сообщения/формы ввода кода приглашения
        на определенных страницах.
        """
        if self.user.is_superuser:
            show_bubble = False
        else:
            show_bubble = True
        monitoring_running = False
        monitoring_name = None
        for o in self.organization.order_by("-id"):
            if o.monitoring.status in (MONITORING_INTERACT,
                                       MONITORING_FINISHING):
                show_bubble = False
            else:
                if not monitoring_running:
                    monitoring_name = o.monitoring.name
            if not monitoring_running and \
               o.monitoring.status in (MONITORING_RATE,
                                       MONITORING_RESULT,
                                       MONITORING_PREPARE):
                monitoring_running = True
                monitoring_name = o.monitoring.name
        return show_bubble, monitoring_running, monitoring_name

    def _get_my_scores(self):
        return Score.objects.filter(task__user=self.user)

    # оценки, к которым имеет доступ ЭкспертБ.
    def _get_my_filtered_scores(self, enum="messages"):
        statuses = []
        if enum == "messages":
            statuses = [MONITORING_PREPARE,
                        MONITORING_PUBLISH]
        elif enum == "comments":
            statuses = [MONITORING_PREPARE,
                        MONITORING_PUBLISH,
                        MONITORING_RATE,
                        MONITORING_RESULT]

        return Score.objects.filter(task__user=self.user).exclude(
                task__organization__monitoring__status__in=statuses)

    def get_answered_comments(self):
        """
        Возвращает queryset из коментов на которые был дан ответ пользователем.
        """
        from custom_comments.models import CommentExmo
        comments = CommentExmo.objects.filter(
            object_pk__in=self._get_my_scores(),
            content_type__model='score',
            status=CommentExmo.ANSWERED,
            user__groups__name=UserProfile.organization_group,
            ).order_by('-submit_date')
        return comments

    def get_not_answered_comments(self):
        """
        Возвращает queryset из коментов на которые еще не был дан ответ.
        """
        from custom_comments.models import CommentExmo
        comments = CommentExmo.objects.filter(
            object_pk__in=self._get_my_scores(),
            content_type__model='score',
            status=CommentExmo.OPEN).order_by('-submit_date')
        return comments

    def get_closed_without_answer_comments(self):
        """
        Возвращает queryset из коментов, которые закрыты без ответа.
        """
        from custom_comments.models import CommentExmo
        comments = CommentExmo.objects.filter(
            object_pk__in=self._get_my_scores(),
            content_type__model='score',
            status=CommentExmo.NOT_ANSWERED).order_by('-submit_date')
        return comments

    def get_opened_claims(self):
        """
        Возвращает queryset из открытых претензий
        """
        claims = Claim.objects.filter(score__task__user=self.user,
                              close_date__isnull=True).order_by('-open_date')
        return claims

    def get_closed_claims(self):
        """
        Возвращает queryset из закрытых претензий
        """
        claims = Claim.objects.filter(addressee=self.user,
            close_date__isnull=False).order_by('-open_date')

        return claims

    def get_opened_clarifications(self):
        """
        Возвращает queryset из открытых уточнений
        """
        clarifications = Clarification.objects.filter(
            score__task__user=self.user,
            close_date__isnull=True).order_by('-open_date')
        return clarifications

    def get_closed_clarifications(self):
        """
        Возвращает queryset из закрытых уточнений
        """
        clarifications = Clarification.objects.filter(score__task__user=self.user,
            close_date__isnull=False).order_by('-open_date')

        return clarifications

    def get_comment_count(self):
        """
        Возвращает количество комментариев в оценках
        """
        answered_comments = self.get_answered_comments().count()
        not_answered_comments = self.get_not_answered_comments().count()
        return answered_comments + not_answered_comments

    def get_claim_count(self):
        """
        Возвращает количество претензий в оценках
        """
        open_claims = self.get_opened_claims().count()
        closed_claims = self.get_closed_claims().count()
        return open_claims + closed_claims

    def get_clarification_count(self):
        """
        Возвращает количество уточнений в оценках
        """
        open_clarifications = self.get_opened_clarifications().count()
        closed_clarifications = self.get_closed_clarifications().count()
        return open_clarifications + closed_clarifications

    def get_filtered_not_answered_comments(self):
        """
        Возвращает queryset из не отвеченных комментариев в соответствующих
        этапах мониторинга, фильтр по этапам нужен для ЭкспертаБ.
        """
        from custom_comments.models import CommentExmo
        comments = CommentExmo.objects.filter(
            object_pk__in=self._get_my_filtered_scores("comments"),
            content_type__model='score',
            status=CommentExmo.OPEN,
            user__groups__name=UserProfile.organization_group,
            ).order_by('submit_date')
        return comments

    def get_filtered_opened_clarifications(self):
        """
        Возвращает queryset из не отвеченных уточнений в соответствующих
        этапах мониторинга, фильтр по этапам нужен для ЭкспертаБ.
        """
        clarifications = Clarification.objects.filter(
            score__task__user=self.user,
            score__in=self._get_my_filtered_scores("messages"),
            close_date__isnull=True).order_by('open_date')
        return clarifications

    def get_filtered_opened_claims(self):
        """
        Возвращает queryset из не отвеченных претензий в соответствующих
        этапах мониторинга, фильтр по этапам нужен для ЭкспертаБ.
        """
        claims = Claim.objects.filter(
            addressee=self.user,
            close_date__isnull=True).order_by('open_date')
        return claims

    def get_task_review_id(self):
        organizations = self.organization.filter(
            monitoring__status__in=[MONITORING_INTERACT,
                                    MONITORING_FINISHING,
                                    MONITORING_PUBLISH])\
        .order_by("-id")
        if organizations:
            organization = organizations[0]
            tasks = Task.objects.filter(
                organization=organization, status=Task.TASK_APPROVED
            )
            if tasks:
                task = tasks[0]
                return task.id

    @property
    def legal_name(self):
        if self.user.first_name and self.user.last_name:
            return u"{0} {1}".format(self.user.first_name, self.user.last_name)
        elif self.user.first_name:
            return u"{0}".format(self.user.first_name)
        elif self.user.last_name:
            return u"{0}".format(self.user.last_name)
        elif self.user.username:
            return u"{0}".format(self.user.username)
        else:
            return u"{0}".format(self.user.email)

    is_expert = property(_is_expert)
    is_expertB = property(_is_expertB)
    is_expertA = property(_is_expertA)
    is_manager_expertB = property(_is_expertA)
    is_customer = property(_is_customer)
    is_organization = property(_is_organization)

    expertA_group = 'expertsA'
    expertB_group = 'expertsB'
    expertB_manager_group = 'expertsB_manager'
    organization_group = 'organizations'
    customer_group = 'customers'

    expert_groups = [expertA_group, expertB_group, expertB_manager_group]

    def __unicode__(self):
        return self.user.username

    class Meta:
        verbose_name = _('user profile')

User.userprofile = property(lambda u: UserProfile.objects.get_or_create(user=u)[0])
User.profile = property(lambda u: UserProfile.objects.get_or_create(user=u)[0])


class MonitoringInteractActivity(models.Model):
    """
    Модель регистрации посещений мониторинга
    """
    monitoring = models.ForeignKey(Monitoring)
    user = models.ForeignKey(User)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.user.userprofile.legal_name,
                             self.monitoring.name)

    class Meta:
        unique_together = ('user', 'monitoring')


from django.db.models.signals import m2m_changed
from django.dispatch import Signal
from tasks.views import task_user_change_notify

def org_changed(sender, instance, action, **kwargs):
    """
    Change organization`s invitation status if current user is the first member of this organization.

    """
    if action == 'post_add':
        for org in instance.organization.all():
            if org.userprofile_set.count():
                org.inv_status = 'RGS'
                org.save()

# invoke signal when 'organization' field at UserProfile was changed
m2m_changed.connect(org_changed, sender=UserProfile.organization.through)

task_user_changed = Signal()
task_user_changed.connect(task_user_change_notify)
