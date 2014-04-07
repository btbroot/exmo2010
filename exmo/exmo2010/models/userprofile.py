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
from django.contrib.auth.models import Group, User, AnonymousUser
from django.db import models
from django.db.models.signals import post_save, m2m_changed
from django.utils.translation import ugettext_lazy as _

from .base import BaseModel
from .claim import Claim
from .clarification import Clarification
from .monitoring import (
    MONITORING_PUBLISHED, MONITORING_PREPARE, MONITORING_INTERACTION,
    MONITORING_FINALIZING, MONITORING_RATE, MONITORING_RESULT)
from .organization import Organization
from .score import Score


def check_role(user, groups):
    if user.is_superuser and 'expert' in ''.join(groups):
        # Superuser have expert rights
        return True
    return bool(set(groups) & set(user.groups.values_list('name', flat=True)))


def group_property(group):
    ''' Create profile property to set and check user relation with given group '''

    def _setter(self, val):
        action = self.user.groups.add if val else self.user.groups.remove
        action(Group.objects.get(name=group))

    _getter = lambda self: check_role(self.user, [group])

    return property(_getter, _setter)


class UserProfile(BaseModel):
    """
    Custom user profile model.

    """
    class Meta(BaseModel.Meta):
        verbose_name = _('user profile')

    SEX_CHOICES = (
        (0, _("not set")),
        (1, _("male")),
        (2, _("female")),
    )

    NOTIFICATION_DISABLE = 0
    NOTIFICATION_ONEBYONE = 1
    NOTIFICATION_DIGEST = 2
    NOTIFICATION_TYPE_CHOICES = (
        (NOTIFICATION_DISABLE, _('do not send')),
        (NOTIFICATION_ONEBYONE, _('one email per one changing')),
        (NOTIFICATION_DIGEST, _('one email for all in time interval')),
    )

    NOTIFICATION_INTERVAL_CHOICES = (
        (1, _("Once in 1 hour")),
        (3, _("Once in 3 hours")),
        (6, _("Once in 6 hours")),
        (12, _("Once in 12 hours")),
        (24, _("Once in 24 hours")),
    )

    LANGUAGE_CHOICES = (
        ('ru', _('Russian')),
        ('en', _('English')),
        ('ka', _('Georgian')),
        ('az', _('Azerbaijani')),
    )

    user = models.ForeignKey(User, unique=True)
    organization = models.ManyToManyField(Organization, null=True, blank=True, verbose_name=_('organizations for view'))
    sex = models.PositiveSmallIntegerField(verbose_name=_("Sex"), choices=SEX_CHOICES, default=0, db_index=True)
    subscribe = models.BooleanField(verbose_name=_("Subscribe to news"), default=False)
    position = models.CharField(verbose_name=_("Job title"), max_length=48,  blank=True)
    phone = models.CharField(verbose_name=_("Phone number"), max_length=30, blank=True)

    # Rating table settings
    rt_representatives = models.BooleanField(verbose_name=_("Representatives"), default=True)
    rt_comment_quantity = models.BooleanField(verbose_name=_("Comment quantity"), default=True)
    rt_initial_openness = models.BooleanField(verbose_name=_("Initial Openness"), default=False)
    rt_final_openness = models.BooleanField(verbose_name=_("Final Openness"), default=True)
    rt_difference = models.BooleanField(verbose_name=_("Difference"), default=True)

    # Change notification settings
    notification_type = models.PositiveSmallIntegerField(verbose_name=_("Notification about changes"),
                                                         choices=NOTIFICATION_TYPE_CHOICES,
                                                         default=NOTIFICATION_DISABLE)
    notification_interval = models.PositiveSmallIntegerField(verbose_name=_("Notification interval"),
                                                             choices=NOTIFICATION_INTERVAL_CHOICES,
                                                             default=1)
    notification_self = models.BooleanField(verbose_name=_("Receive a notice about self changes"), default=False)
    notification_thread = models.BooleanField(verbose_name=_("Send whole comment thread"), default=False)
    digest_date_journal = models.DateTimeField(verbose_name=_('Last digest sending date'), blank=True, null=True)
    # language locale settings
    language = models.CharField(verbose_name=_('Language'), choices=LANGUAGE_CHOICES,
                                max_length=2, blank=True, null=True)

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
            if o.monitoring.status in (MONITORING_INTERACTION,
                                       MONITORING_FINALIZING):
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
                        MONITORING_PUBLISHED]
        elif enum == "comments":
            statuses = [MONITORING_PREPARE,
                        MONITORING_PUBLISHED,
                        MONITORING_RATE,
                        MONITORING_RESULT]

        return Score.objects.filter(task__user=self.user).exclude(task__organization__monitoring__status__in=statuses)

    def get_answered_comments(self):
        """
        Возвращает queryset из коментов на которые был дан ответ пользователем.
        """
        from custom_comments.models import CommentExmo
        return CommentExmo.objects.order_by('-submit_date').filter(
            object_pk__in=self._get_my_scores(),
            content_type__model='score',
            status=CommentExmo.ANSWERED,
            user__groups__name=UserProfile.organization_group)

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
        return CommentExmo.objects.order_by('submit_date').filter(
            object_pk__in=self._get_my_filtered_scores("comments"),
            content_type__model='score',
            status=CommentExmo.OPEN,
            user__groups__name=UserProfile.organization_group)

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
        from .task import Task
        organizations = self.organization.filter(
            monitoring__status__in=[MONITORING_INTERACTION,
                                    MONITORING_FINALIZING,
                                    MONITORING_PUBLISHED])\
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

    expertA_group = 'expertsA'
    expertB_group = 'expertsB'
    organization_group = 'organizations'
    customer_group = 'customers'

    expert_groups = [expertA_group, expertB_group]

    is_expert = property(lambda self: check_role(self.user, self.expert_groups))
    is_expertB = group_property(expertB_group)
    is_expertA = group_property(expertA_group)
    is_customer = group_property(customer_group)
    is_organization = group_property(organization_group)

    is_internal = lambda self: self.user.is_superuser or self.user.is_staff or self.is_expert

    def __unicode__(self):
        return self.user.username


def create_user_profile(sender, instance, created, **kwargs):
    """
    Create user profile for new users at save user time, if it doesn't already exist
    """
    if created:
        UserProfile(user=instance).save()


post_save.connect(create_user_profile, sender=User)

User.userprofile = property(lambda u: u.get_profile())
User.profile = property(lambda u: u.get_profile())

User.legal_name = property(lambda u: u.profile.legal_name)

User.is_expert = property(lambda u: u.is_active and u.profile.is_expert)
User.is_expertB = property(lambda u: u.is_active and u.profile.is_expertB)
User.is_expertA = property(lambda u: u.is_active and u.profile.is_expertA)
User.is_customer = property(lambda u: u.is_active and u.profile.is_customer)
User.is_organization = property(lambda u: u.is_active and u.profile.is_organization)
User.represents = lambda u, org: u.is_active and u.profile.organization.filter(pk=org.pk).exists()
User.executes = lambda u, task: u.is_expertB and task.user_id == u.pk

AnonymousUser.is_expert = False
AnonymousUser.is_expertB = False
AnonymousUser.is_expertA = False
AnonymousUser.is_customer = False
AnonymousUser.is_organization = False
AnonymousUser.represents = lambda u, org: False
AnonymousUser.executes = lambda u, task: False


def org_changed(sender, instance, action, **kwargs):
    """
    Change organization`s invitation status if current user is the first member of this organization.

    """
    if action == 'post_add':
        instance.organization.exclude(inv_status='ACT')\
                             .filter(userprofile__isnull=False)\
                             .update(inv_status='RGS')

# invoke signal when 'organization' field at UserProfile was changed
m2m_changed.connect(org_changed, sender=UserProfile.organization.through)
