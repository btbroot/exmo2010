# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2016 IRSI LTD
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
from django.contrib import auth
from django.contrib.auth.models import Group, User, AnonymousUser
from django.db.models import (
    ForeignKey, PositiveSmallIntegerField, CharField, BooleanField, ManyToManyField, OneToOneField, DateTimeField)
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from .base import BaseModel
from .claim import Claim
from .clarification import Clarification
from .monitoring import PRE, RATE, RES, INT, FIN
from .organization import Organization
from .score import Score

from ..columns_picker import ColumnsPickerModel


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


class OrgUser(BaseModel):
    """
    UserProfile-to-Organization M2M realtionship model.
    """
    class Meta(BaseModel.Meta):
        unique_together = ('userprofile', 'organization')
    userprofile = ForeignKey("UserProfile")
    organization = ForeignKey("Organization")

    # Seen by default is True to ease testing. It is only set to False explicitly when
    # monitoring is copied. Will be reset to True in OrguserTrackingMiddleware.
    seen = BooleanField(default=True)


class UserProfile(BaseModel, ColumnsPickerModel):
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

    user = OneToOneField(User)
    # email_confirmed is True by default to ease tests. After regular registration this field is set to False.
    email_confirmed = BooleanField(default=True)
    organization = ManyToManyField(Organization, through=OrgUser, null=True, blank=True, verbose_name=_('organizations for view'))
    sex = PositiveSmallIntegerField(verbose_name=_("Sex"), choices=SEX_CHOICES, default=0, db_index=True)
    subscribe = BooleanField(verbose_name=_("Subscribe to news"), default=False)
    position = CharField(verbose_name=_("Job title"), max_length=48, null=True, blank=True)
    phone = CharField(verbose_name=_("Phone number"), max_length=30, null=True, blank=True)

    # Change notification settings
    notification_type = PositiveSmallIntegerField(verbose_name=_("Notification about changes"),
                                                  choices=NOTIFICATION_TYPE_CHOICES,
                                                  default=NOTIFICATION_DISABLE)
    notification_interval = PositiveSmallIntegerField(verbose_name=_("Notification interval"),
                                                      choices=NOTIFICATION_INTERVAL_CHOICES,
                                                      default=1)
    notification_self = BooleanField(verbose_name=_("Receive a notice about self changes"), default=False)
    notification_thread = BooleanField(verbose_name=_("Send whole comment thread"), default=False)
    digest_date_journal = DateTimeField(verbose_name=_('Last digest sending date'), blank=True, null=True)
    # language locale settings
    language = CharField(verbose_name=_('Language'), choices=LANGUAGE_CHOICES,
                         max_length=2, blank=True, null=True)
    show_interim_score = BooleanField(verbose_name=_("Show initial scores"), default=False)

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
            if o.monitoring.status in (INT, FIN):
                show_bubble = False
            else:
                if not monitoring_running:
                    monitoring_name = o.monitoring.name
            if not monitoring_running and \
               o.monitoring.status in (PRE, RATE, RES):
                monitoring_running = True
                monitoring_name = o.monitoring.name
        return show_bubble, monitoring_running, monitoring_name

    def get_opened_comments(self):
        """
        Возвращает queryset из коментов представителей организаций на которые не был дан ответ
        """
        from custom_comments.models import CommentExmo
        return CommentExmo.objects.filter(object_pk__in=Score.objects.filter(task__user=self.user),
                                          content_type__model='score',
                                          user__groups__name=UserProfile.organization_group,
                                          status=CommentExmo.OPEN)\
                                  .order_by('submit_date')

    def get_answered_comments(self):
        """
        Возвращает queryset из коментов представителей организаций на которые был дан ответ экспертом
        """
        from custom_comments.models import CommentExmo
        return CommentExmo.objects.filter(object_pk__in=Score.objects.filter(task__user=self.user),
                                          content_type__model='score',
                                          user__groups__name=UserProfile.organization_group,
                                          status=CommentExmo.ANSWERED)\
                                  .order_by('-submit_date')

    def get_opened_clarifications(self):
        """
        Возвращает queryset из открытых уточнений
        """
        return Clarification.objects.filter(score__task__user=self.user, close_date__isnull=True)\
                                    .order_by('open_date')

    def get_closed_clarifications(self):
        """
        Возвращает queryset из закрытых уточнений
        """
        return Clarification.objects.filter(score__task__user=self.user, close_date__isnull=False)\
                                    .order_by('-open_date')

    def get_opened_claims(self):
        """
        Возвращает queryset из открытых претензий
        """
        return Claim.objects.filter(addressee=self.user, close_date__isnull=True).order_by('open_date')

    def get_closed_claims(self):
        """
        Возвращает queryset из закрытых претензий
        """
        return Claim.objects.filter(addressee=self.user, close_date__isnull=False).order_by('-open_date')

    def _get_full_name(self, first_name_first=False):
        name_list = filter(None, [self.user.last_name.strip(), self.user.first_name.strip()])
        if name_list:
            if first_name_first:
                name_list.reverse()
            result = ' '.join(unicode(s) for s in name_list)
        else:
            result = self.user.username if self.user.username else self.user.email

        return result

    @property
    def legal_name(self):
        return self._get_full_name(first_name_first=True)

    @property
    def full_name(self):
        return self._get_full_name()

    expertA_group = 'expertsA'
    expertB_group = 'expertsB'
    customer_group = 'customers'
    translator_group = 'translators'
    organization_group = 'organizations'

    expert_groups = [expertA_group, expertB_group]

    is_expert = property(lambda self: check_role(self.user, self.expert_groups))
    is_expertA = group_property(expertA_group)
    is_expertB = group_property(expertB_group)
    is_customer = group_property(customer_group)
    is_translator = group_property(translator_group)
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

User.profile = property(lambda u: u.userprofile)

User.legal_name = property(lambda u: u.profile.legal_name)
User.full_name = property(lambda u: u.profile.full_name)

User.is_expert = property(lambda u: u.is_active and u.profile.is_expert)
User.is_expertB = property(lambda u: u.is_active and u.profile.is_expertB)
User.is_expertA = property(lambda u: u.is_active and u.profile.is_expertA)
User.is_customer = property(lambda u: u.is_active and u.profile.is_customer)
User.is_translator = property(lambda u: u.is_active and u.profile.is_translator)
User.is_organization = property(lambda u: u.is_active and u.profile.is_organization)
User.represents = lambda u, org: u.is_active and u.profile.organization.filter(pk=org.pk).exists()
User.observes = lambda u, org: u.is_active and org.observersgroup_set.filter(users=u).exists()
User.executes = lambda u, task: u.is_expertB and task.user_id == u.pk

# TODO: get rid of monkey-patching User.has_perm, instead use Django 1.5 User model customization.
# Monkey-patch has_perm to force checking exmo2010 perms for superuser.
User.has_perm = lambda u, perm, obj=None: _user_has_perm(u, perm, obj)


AnonymousUser.is_expert = False
AnonymousUser.is_expertB = False
AnonymousUser.is_expertA = False
AnonymousUser.is_customer = False
AnonymousUser.is_organization = False
AnonymousUser.represents = lambda u, org: False
AnonymousUser.observes = lambda u, org: False
AnonymousUser.executes = lambda u, task: False


# TODO: get rid of monkey-patching User.has_perm, instead use Django 1.5 User model customization.
def _user_has_perm(user, perm, obj):
    # Mimic old behavior for non-exmo2010 perms. Always True for superuser.
    if user.is_superuser and not perm.startswith('exmo2010.'):
        return True

    for backend in auth.get_backends():
        if hasattr(backend, "has_perm"):
            if obj is not None:
                if backend.has_perm(user, perm, obj):
                    return True
            else:
                if backend.has_perm(user, perm):
                    return True
    return False


# NOTE: Currently it is impossible to use add(), create(), etc. with custom M2M relation model, see
# https://code.djangoproject.com/ticket/9475
# Having custom OrgUser relation model force us to instantinate it directly insetad of using add()
# method, so `m2m_changed` signal became useless. We should use post_save on OrgUser instead.

def orguser_saved(sender, instance, created, **kwargs):
    """
    Change organization`s invitation status if current user is the first seen member of this organization.

    """
    if instance.seen and not instance.organization.inv_status == 'ACT':
        instance.organization.inv_status = 'RGS'
        instance.organization.save()


post_save.connect(orguser_saved, sender=OrgUser)
