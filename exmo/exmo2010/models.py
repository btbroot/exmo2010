# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
EXMO2010 Models module
"""

from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext as _
from tagging.models import Tag
from exmo2010.fields import TagField
from exmo2010.utils import get_stat_answered_comments, get_org_comments



class OpennessExpression(models.Model):
  code    = models.PositiveIntegerField(primary_key=True)
  name    = models.CharField(max_length = 255, default = "-", verbose_name=_('name'))

  def __unicode__(self):
    return _('%(name)s (from EXMO2010 v%(code)d)') % { 'name': self.name, 'code': self.code }



class Monitoring(models.Model):
  MONITORING_PREPARE   = 0
  MONITORING_RATE      = 1
  MONITORING_REVISION  = 2
  MONITORING_INTERACT  = 3
  MONITORING_RESULT    = 4
  MONITORING_PUBLISH   = 5
  MONITORING_PLANNED   = 6
  MONITORING_STATUS    = (
        (MONITORING_PREPARE, _('prepare')),
        (MONITORING_RATE, _('rate')),
        (MONITORING_REVISION, _('revision')),
        (MONITORING_INTERACT, _('interact')),
        (MONITORING_RESULT, _('result')),
        (MONITORING_PUBLISH, _('publish')),
  )
  MONITORING_STATUS_FULL = MONITORING_STATUS + ((MONITORING_PLANNED, _('planned')),)
  MONITORING_STATUS_NEW  = (MONITORING_STATUS_FULL[0],) + (MONITORING_STATUS_FULL[6],)

  name                   = models.CharField(max_length = 255, default = "-", verbose_name=_('name'))
  status                 = models.PositiveIntegerField(choices = MONITORING_STATUS_FULL, default = MONITORING_PLANNED, verbose_name=_('status'))
  openness_expression    = models.ForeignKey(
    OpennessExpression,
    default = 8,
    verbose_name=_('openness expression'),
  )

  def __unicode__(self):
    return '%s' % self.name

  @models.permalink
  def get_absolute_url(self):
    return ('exmo2010:tasks_by_monitoring', [str(self.id)])

  def create_calendar(self):
    for status in self.MONITORING_STATUS:
        MonitoringStatus.objects.get_or_create(status = status[0], monitoring = self)

  def _get_prepare(self):
    return self.status == self.MONITORING_PREPARE

  def _get_rate(self):
    return self.status == self.MONITORING_RATE

  def _get_revision(self):
    return self.status == self.MONITORING_REVISION

  def _get_interact(self):
    return self.status == self.MONITORING_INTERACT

  def _get_result(self):
    return self.status == self.MONITORING_RESULT

  def _get_publish(self):
    return self.status == self.MONITORING_PUBLISH

  def _get_planned(self):
    return self.status == self.MONITORING_PLANNED

  def _get_active(self):
    return not (self.is_prepare or self.is_planned)

  after_interaction_status = [MONITORING_INTERACT, MONITORING_RESULT, MONITORING_PUBLISH]

  is_prepare = property(_get_prepare)
  is_rate = property(_get_rate)
  is_revision = property(_get_revision)
  is_interact = property(_get_interact)
  is_result = property(_get_result)
  is_publish = property(_get_publish)
  is_planned = property(_get_planned)

  is_active = property(_get_active)

  class Meta:
    ordering = ('name',)



class MonitoringStatus(models.Model):
    monitoring   = models.ForeignKey(Monitoring, verbose_name=_('monitoring'))
    status       = models.PositiveIntegerField(choices = Monitoring.MONITORING_STATUS, default = Monitoring.MONITORING_PREPARE, verbose_name=_('status'))
    start        = models.DateTimeField(null = True, blank=True, verbose_name=_('start at'))

    def __unicode__(self):
        for status in Monitoring.MONITORING_STATUS_FULL:
            if status[0] == self.status: return "%s: %s" % (self.monitoring.name, status[1])

    class Meta:
        unique_together = (
            ('status', 'monitoring'),
        )
        ordering = (
            '-start',
        )



class Organization(models.Model):
  """ Fields:
  name -- Uniq organization name
  url -- Internet site URL
  keywords -- Keywords for autocomplete and search
  comments -- Additional comment
  """

  name         = models.CharField(max_length = 255, verbose_name=_('name'))
  url          = models.URLField(max_length = 255, null = True, blank = True, verify_exists = False, verbose_name=_('url'))
  keywords     = TagField(null = True, blank = True, verbose_name = _('keywords'))
  comments     = models.TextField(null = True, blank = True, verbose_name=_('comments'))
  monitoring   = models.ForeignKey(Monitoring, verbose_name=_('monitoring'))

#I dont know why, but this breaks reversion while import-(
  def __unicode__(self):
    return '%s' % (self.name)

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



class Parameter(models.Model):
  code               = models.PositiveIntegerField(verbose_name=_('code'))
  #db_index=False -- MySQL get error: "Specified key was too long; max key length is 1000 bytes" for long varchar field
  name               = models.CharField(max_length = 1000, verbose_name=_('name'), db_index=False)
  description        = models.TextField(null = True, blank = True, verbose_name=_('description'))
  monitoring         = models.ForeignKey(Monitoring, verbose_name=_('monitoring'))
  exclude            = models.ManyToManyField(Organization, null = True, blank = True, verbose_name=_('excluded organizations'))
  weight             = models.IntegerField(verbose_name=_('weight'))
  keywords           = TagField(null = True, blank = True, verbose_name = _('keywords'))
  complete           = models.BooleanField(default = True, verbose_name=_('complete'))
  topical            = models.BooleanField(default = True, verbose_name=_('topical'))
  accessible         = models.BooleanField(default = True, verbose_name=_('accessible'))
  hypertext          = models.BooleanField(default = True, verbose_name=_('hypertext'))
  document           = models.BooleanField(default = True, verbose_name=_('document'))
  image              = models.BooleanField(default = True, verbose_name=_('image'))

#I dont know why, but this breaks reversion while import-(
  def __unicode__(self):
    return "%s" % self.name

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
  def get_query_set(self):
        return super(OpenTaskManager, self).get_query_set().filter(status = Task.TASK_OPEN)



class ReadyTaskManager(models.Manager):
  def get_query_set(self):
        return super(ReadyTaskManager, self).get_query_set().filter(status = Task.TASK_READY)



class ApprovedTaskManager(models.Manager):
  def get_query_set(self):
        return super(ApprovedTaskManager, self).get_query_set().filter(status = Task.TASK_APPROVED)



from django.db.models import Count
class Task(models.Model):
  TASK_OPEN       = 0
  TASK_READY      = TASK_CLOSE = TASK_CLOSED = 1
  TASK_APPROVED   = TASK_APPROVE = 2
  TASK_CHECK      = TASK_CHECKED = 3
  TASK_STATUS     = (
    (TASK_OPEN, _('opened')),
    (TASK_CLOSE, _('closed')),
    (TASK_CHECK, _('check')),
    (TASK_APPROVE, _('approved'))
  )
  user         = models.ForeignKey(User, verbose_name=_('user'))
  organization = models.ForeignKey(Organization, verbose_name=_('organization'))
  status       = models.PositiveIntegerField(choices = TASK_STATUS, default = TASK_OPEN, verbose_name=_('status'))
  openness_cache     = models.FloatField(null = True, blank = True, default = 0, editable = False, verbose_name = _('openness'))

  def _openness(self):
    openness = 0
    scores = Score.objects.filter(
        revision = Score.REVISION_DEFAULT,
        task = self,
        parameter__in = Parameter.objects.filter(
            monitoring = self.organization.monitoring
        ).exclude(exclude = self.organization)
    ).select_related()
    openness_actual = sum([openness_helper(s) for s in scores])
    parameters_weight = Parameter.objects.exclude(exclude = self.organization).filter(monitoring = self.organization.monitoring, weight__gte = 0)
    openness_max = sum([parameter_weight.weight for parameter_weight in parameters_weight])
    if openness_max:
        openness = float(openness_actual * 100) / openness_max
    return openness

  def _get_openness(self):
    if not self.openness_cache:
        self.update_openness()
    return self.openness_cache

  def update_openness(self):
        self.openness_cache = self._openness()
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

  def _get_open(self):
    if self.status == self.TASK_OPEN: return True
    else: return False

  def _get_ready(self):
    if self.status == self.TASK_READY: return True
    else: return False

  def _get_approved(self):
    if self.status == self.TASK_APPROVED: return True
    else: return False

  def _get_checked(self):
    if self.status == self.TASK_CHECK: return True
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

  def _set_checked(self, val):
    if val:
        self.status = self.TASK_CHECKED
        self.full_clean()
        self.save()

  @property
  def complete(self):
    complete = 0
    parameters = Parameter.objects.filter(monitoring = self.organization.monitoring).exclude(exclude = self.organization).count()
    if parameters:
        scores_count = Score.objects.filter(
            task=self,
            revision=Score.REVISION_DEFAULT,
        ).exclude(
            parameter__exclude=self.organization
        ).count()
        complete = scores_count * 100.0 / parameters
    return complete

  @property
  def rating_place(self):
    from exmo2010.view.helpers import rating
    place = None
    rating_list, avg = rating(self.organization.monitoring)
    for rating_object in rating_list:
          if rating_object['task'] == self:
            place = rating_object['place']
            break
    return place

  open = property(_get_open, _set_open)
  ready = property(_get_ready, _set_ready)
  checked = property(_get_checked, _set_checked)
  approved = property(_get_approved, _set_approved)
  openness = property(_get_openness)



class Score(models.Model):

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
        verbose_name=_('comment'),
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
        claims=self.claim_count()
        if claims > 0:
            return True
        else:
            return False

    def _get_openness(self):
        return openness_helper(self)

    def add_claim(self, creator, comment):
        claim = Claim(score=self, creator=creator, comment=comment)
        claim.full_clean()
        claim.save()
        return claim

    def close_claim(self, close_user):
        import datetime
        #score has active claims and form cames to us with changed data. we expect that new data resolv claims.
        for claim in Claim.objects.filter(score=self, close_date__isnull=True):
            claim.close_date = datetime.datetime.now()
            claim.close_user = close_user
            claim.full_clean()
            claim.save()

    def claim_count(self):
        return Claim.objects.filter(score=self, close_date__isnull=True).count()

    def claim_color(self):
        color = None
        if self.active_claim:
            color = 'red'
        elif not self.active_claim and Claim.objects.filter(score=self).count() > 0:
            color = 'green'
        elif not self.active_claim and Claim.objects.filter(score=self).exclude(close_user=self.task.user).count() > 0:
            color = 'yellow'
        return color

    def create_revision(self, revision):
        if self.task.organization.monitoring.status in Monitoring.after_interaction_status \
          and revision == Score.REVISION_INTERACT:
            revision_score = Score.objects.filter(
                task=self.task,
                parameter=self.parameter,
                revision=revision,
            )
            if not revision_score:
                revision_score = Score.objects.get(pk=self.pk)
                revision_score.pk = None
                revision_score.revision = revision
                revision_score.full_clean()
                revision_score.save()

    @property
    def have_comment_without_reply(self):
        self_comments_qs = Comment.objects.select_related().filter(
            object_pk = self.pk,
            content_type = ContentType.objects.get_for_model(self.__class__)
        ).order_by('-submit_date')
        if self_comments_qs.count() > 0:
            #check first comment is from organization
            if self_comments_qs[0].user.groups.filter(name=UserProfile.organization_group).count() > 0:
                return self_comments_qs[0].pk
        return False

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
  "Модель претензий/замечаний"
  score             = models.ForeignKey(Score, verbose_name=_('score'))
  "Оценка"
  open_date         = models.DateTimeField(auto_now_add = True, verbose_name = _('claim open'))
  "Дата создания"
  close_date        = models.DateTimeField(null = True, blank = True, verbose_name = _('claim close'))
  "Дата закрытия. По её наличию определяется закрыта претензия или нет"
  comment           = models.TextField(null = True, blank = True, verbose_name=_('comment'))
  "Комментарий"
  close_user        = models.ForeignKey(User, null = True, blank = True, verbose_name=_('user who close'), related_name='close_user')
  "Кто закрыл претензию"
  creator           = models.ForeignKey(User, verbose_name=_('creator'), related_name='creator')
  "Кто создал претензию"

  def __unicode__(self):
    return _('claim for %(score)s from %(creator)s') % { 'score': self.score, 'creator': self.creator }

  class Meta:
    permissions = (("view_claim", "Can view claim"),)



def openness_helper(score):
    "Враппер для расчета КО"
    f = eval("openness_helper_v%d" % score.task.organization.monitoring.openness_expression.code)
    return f(score)



def openness_helper_v1(score):
    """Превая версия формулы расчета КО

    Не учитывает доступность в граф. формате
    """
    found = score.found
    weight = score.parameter.weight
    complete = 1
    topical = 1
    accessible = 1
    format = 1
    if score.parameter.complete:
        if score.complete == 1: complete = 0.2
        if score.complete == 2: complete = 0.5
        if score.complete == 3: complete = 1
    if score.parameter.topical:
        if score.topical == 1: topical = 0.7
        if score.topical == 2: topical = 0.85
        if score.topical == 3: topical = 1
    if score.parameter.accessible:
        if score.accessible == 1: accessible = 0.9
        if score.accessible == 2: accessible = 0.95
        if score.accessible == 3: accessible = 1
    if score.parameter.hypertext:
        if score.parameter.document:
            if score.hypertext == 0:
                if score.document == 0: format = 0.2
                if score.document == 1: format = 0.2
            if score.hypertext == 1:
                if score.document == 0: format = 0.9
                if score.document == 1: format = 1
        else:
            if score.hypertext == 0: format = 0.2
            if score.hypertext == 1: format = 1
    openness = weight * found * complete * topical * accessible * format
    return openness



def openness_helper_v8(score):
    "Вторая версия расчета КО"
    found = score.found
    weight = score.parameter.weight
    complete = 1
    topical = 1
    accessible = 1
    format_html = 1
    format_doc = 1
    format_image = 1
    if score.parameter.complete:
        if score.complete == 1: complete = 0.2
        if score.complete == 2: complete = 0.5
        if score.complete == 3: complete = 1
    if score.parameter.topical:
        if score.topical == 1: topical = 0.7
        if score.topical == 2: topical = 0.85
        if score.topical == 3: topical = 1
    if score.parameter.accessible:
        if score.accessible == 1: accessible = 0.9
        if score.accessible == 2: accessible = 0.95
        if score.accessible == 3: accessible = 1
    if score.parameter.hypertext:
        if score.hypertext == 0: format_html = 0.2
        if score.hypertext == 1: format_html = 1
    if score.parameter.document:
        if score.document == 0: format_doc = 0.85
        if score.document == 1: format_doc = 1
    if score.parameter.image:
        if score.image == 0: format_image = 0.95
        if score.image == 1: format_image = 1
    openness = weight * found * complete * topical * accessible * format_html * format_doc * format_image
    return openness



from digest_email.models import Digest, DigestPreference
from django.contrib.auth.models import Group
import json

SEX_CHOICES = (
    (0, _("not set")),
    (1, _("male")),
    (2, _("female")),
    (3, _("other")),
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
    preference = models.TextField(null=True, blank=True,
        verbose_name=_('preference'))
    sex = models.PositiveSmallIntegerField(verbose_name=_("Sex"),
        choices=SEX_CHOICES, default=0, db_index=True)

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
            pref['digest_duratation'] = 5
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
        return self._is_expertB() or self._is_expertA() or self._is_manager_expertB() or self.user.is_superuser

    def _is_expertB(self):
        try:
            group, created = Group.objects.get_or_create(name=self.expertB_group)
        except:
            return False
        else:
            return group in self.user.groups.all() or self.user.is_superuser

    def _is_expertA(self):
        try:
            group, created = Group.objects.get_or_create(name=self.expertA_group)
        except:
            return False
        else:
            return group in self.user.groups.all() or self.user.is_superuser

    def _is_manager_expertB(self):
        try:
            group, created = Group.objects.get_or_create(name=self.expertB_manager_group)
        except:
            return False
        else:
            return group in self.user.groups.all() or self.user.is_superuser

    def _is_customer(self):
        try:
            group, created = Group.objects.get_or_create(name=self.customer_group)
        except:
            return False
        else:
            return group in self.user.groups.all() or self.user.is_superuser

    def _is_organization(self):
        try:
            group, creater = Group.objects.get_or_create(name=self.organization_group)
        except:
            return False
        else:
            return group in self.user.groups.all() or self.user.is_superuser

    def _get_my_scores(self):
        return Score.objects.filter(task__user=self.user)

    def get_answered_comments(self):
        """
        Возвращает queryset из коментов на которые был дан ответ пользователем
        """
        org_comments = get_org_comments()
        stat = get_stat_answered_comments()
        return org_comments.filter(object_pk__in=self._get_my_scores(),
            pk__in=stat['answered']).order_by('-submit_date')

    def get_not_answered_comments(self):
        """
        Возвращает queryset из коментов на которые еще не был дан ответ
        """
        org_comments = get_org_comments()
        stat = get_stat_answered_comments()
        return org_comments.filter(object_pk__in=self._get_my_scores(),
            pk__in=stat['not_answered']).order_by('submit_date')

    def get_opened_claims(self):
        """
        Возвращает queryset из открытых претензий
        """
        claims = Claim.objects.filter(
            score__task__user=self,
            close_date__isnull=True,
        ).order_by('-open_date')
        return claims

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
