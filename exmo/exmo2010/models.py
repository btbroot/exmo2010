# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 Institute for Information Freedom Development
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
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from exmo.exmo2010.fields import TagField
from tagging.models import Tag



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

  is_prepare = property(_get_prepare)
  is_rate = property(_get_rate)
  is_revision = property(_get_revision)
  is_interact = property(_get_interact)
  is_result = property(_get_result)
  is_publish = property(_get_publish)
  is_planned = property(_get_planned)

  is_active = property(_get_active)



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
  '''
  name -- Uniq organization name
  url -- Internet site URL
  keywords -- Keywords for autocomplete and search
  comments -- Additional comment
  '''

  name         = models.CharField(max_length = 255, verbose_name=_('name'))
  url          = models.URLField(max_length = 255, null = True, blank = True, verify_exists = False, verbose_name=_('url'))
  keywords     = TagField(null = True, blank = True, verbose_name = _('keywords'))
  comments     = models.TextField(null = True, blank = True, verbose_name=_('comments'))
  monitoring   = models.ForeignKey(Monitoring, verbose_name=_('monitoring'))

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

#I dont know why, but this breaks reversion-(
#  def __unicode__(self):
#    return "%s" % self.name

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
    (TASK_CHECK, _('checked')),
    (TASK_APPROVE, _('approved'))
  )
  user         = models.ForeignKey(User, verbose_name=_('user'))
  organization = models.ForeignKey(Organization, verbose_name=_('organization'))
  status       = models.PositiveIntegerField(choices = TASK_STATUS, default = TASK_OPEN, verbose_name=_('status'))
  openness_cache     = models.FloatField(null = True, blank = True, default = 0, editable = False, verbose_name = _('openness'))

  def _openness(self):
    openness = 0
    scores = Score.objects.filter(
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

  def _complete(self):
    complete = 0
    parameters = Parameter.objects.filter(monitoring = self.organization.monitoring).exclude(exclude = self.organization).count()
    if parameters:
        complete = float(Score.objects.filter(task = self).exclude(parameter__exclude = self.organization).count() * 100) / parameters
    return complete

  open = property(_get_open, _set_open)
  ready = property(_get_ready, _set_ready)
  checked = property(_get_checked, _set_checked)
  approved = property(_get_approved, _set_approved)
  openness = property(_get_openness)
  complete = property(_complete)



class Score(models.Model):
  task              = models.ForeignKey(Task, verbose_name=_('task'))
  parameter         = models.ForeignKey(Parameter, verbose_name=_('parameter'))
  found             = models.IntegerField(choices = ((0, 0), (1, 1)), verbose_name=_('found'))
  complete          = models.IntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)), verbose_name=_('complete'))
  completeComment   = models.TextField(null = True, blank = True, verbose_name=_('completeComment'))
  topical           = models.IntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)), verbose_name=_('topical'))
  topicalComment    = models.TextField(null = True, blank = True, verbose_name=_('topicalComment'))
  accessible        = models.IntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)), verbose_name=_('accessible'))
  accessibleComment = models.TextField(null = True, blank = True, verbose_name=_('accessibleComment'))
  hypertext         = models.IntegerField(null = True, blank = True, choices = ((0, 0), (1, 1)), verbose_name=_('hypertext'))
  hypertextComment  = models.TextField(null = True, blank = True, verbose_name=_('hypertextComment'))
  document          = models.IntegerField(null = True, blank = True, choices = ((0, 0), (1, 1)), verbose_name=_('document'))
  documentComment   = models.TextField(null = True, blank = True, verbose_name=_('documentComment'))
  image             = models.IntegerField(null = True, blank = True, choices = ((0, 0), (1, 1)), verbose_name=_('image'))
  imageComment      = models.TextField(null = True, blank = True, verbose_name=_('imageComment'))
  comment           = models.TextField(null = True, blank = True, verbose_name=_('comment'))

  def __unicode__(self):
    return '%s: %s [%d]' % (
      self.task.user.username,
      self.task.organization.name,
      self.parameter.code
    )

  def clean(self):
    if self.found:
      if self.parameter.complete   and self.complete   in ('', None):
        raise ValidationError(_('Complete must be set'))
      if self.parameter.topical    and self.topical    in ('', None):
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
        self.complete!=None,
        self.topical!=None,
        self.accessible!=None,
        self.hypertext!=None,
        self.document!=None,
        self.image!=None,
        self.completeComment,
        self.topicalComment,
        self.accessibleComment,
        self.hypertextComment,
        self.documentComment,
        self.imageComment,
        )):
      raise ValidationError(_('Not found, but some excessive data persists'))

  def _get_claim(self):
    claims=self.claim_count()
    if claims > 0:
        return True
    else: return False

  def _get_openness(self):
    return openness_helper(self)

  def add_claim(self, creator, comment):
    claim = Claim(score = self, creator = creator, comment = comment)
    claim.full_clean()
    claim.save()
    return claim

  def close_claim(self, close_user):
    import datetime
    #score has active claims and form cames to us with changed data. we expect that new data resolv claims.
    for claim in Claim.objects.filter(score = self, close_date__isnull = True):
        claim.close_date=datetime.datetime.now()
        claim.close_user=close_user
        claim.full_clean()
        claim.save()

  def claim_count(self):
    return Claim.objects.filter(score=self, close_date__isnull = True).count()

  def claim_color(self):
    color = None
    if self.active_claim: color = 'red'
    if not self.active_claim and Claim.objects.filter(score = self).count() > 0: color = 'green'
    if not self.active_claim and Claim.objects.filter(score = self).exclude(close_user = self.task.user).count() > 0: color = 'yellow'
    return color

  active_claim = property(_get_claim)
  openness = property(_get_openness)

  class Meta:
    unique_together = (
      ('task', 'parameter'),
    )
    ordering = (
      'task__user__username',
      'task__organization__name',
      'parameter__code'
    )
    permissions = (("view_score", "Can view score"),)



class Claim(models.Model):
  score             = models.ForeignKey(Score, verbose_name=_('score'))
  open_date         = models.DateTimeField(auto_now = True, verbose_name = _('claim open'))
  close_date        = models.DateTimeField(null = True, blank = True, verbose_name = _('claim close'))
  comment           = models.TextField(null = True, blank = True, verbose_name=_('comment'))
  close_user        = models.ForeignKey(User, null = True, blank = True, verbose_name=_('user who close'), related_name='close_user')
  creator           = models.ForeignKey(User, verbose_name=_('creator'), related_name='creator')

  def __unicode__(self):
    return _('claim for %(score)s from %(creator)s') % { 'score': self.score, 'creator': self.creator }

  class Meta:
    permissions = (("view_claim", "Can view claim"),)



def openness_helper(score):
    f = eval("openness_helper_v%d" % score.task.organization.monitoring.openness_expression.code)
    return f(score)



def openness_helper_v1(score):
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



from django.contrib.auth.models import Group
class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)

    organization = models.ManyToManyField(Organization, null = True, blank = True, verbose_name=_('organizations for view'))
    notify_score_change = models.BooleanField(blank = True, default = False, verbose_name=_('notify score change'))
    notify_self_comment = models.BooleanField(blank = True, default = True, verbose_name=_('notify on self comment'))
    notify_comment = models.BooleanField(blank = True, default = True, verbose_name=_('notify on comment, except self'))

    def _is_expert(self):
        return self._is_expertB() or self._is_expertA() or self._is_manager_expertB()

    def _is_expertB(self):
        try:
            group, created = Group.objects.get_or_create(name=self.expertB_group)
        except:
            return False
        else:
            return group in self.user.groups.all()

    def _is_expertA(self):
        try:
            group, created = Group.objects.get_or_create(name=self.expertA_group)
        except:
            return False
        else:
            return group in self.user.groups.all()

    def _is_manager_expertB(self):
        try:
            group, created = Group.objects.get_or_create(name=self.expertB_manager_group)
        except:
            return False
        else:
            return group in self.user.groups.all()

    def _is_customer(self):
        try:
            group, created = Group.objects.get_or_create(name=self.customer_group)
        except:
            return False
        else:
            return group in self.user.groups.all()

    def _is_organization(self):
        try:
            group, creater = Group.objects.get_or_create(name=self.organization_group)
        except:
            return False
        else:
            return group in self.user.groups.all()



    is_expert = property(_is_expert)
    is_expertB = property(_is_expertB)
    is_expertA = property(_is_expertA)
    is_manager_expertB = property(_is_manager_expertB)
    is_customer = property(_is_customer)
    is_organization = property(_is_organization)

    expertA_group = 'expertsA'
    expertB_group = 'expertsB'
    expertB_manager_group = 'expertsB_manager'
    organization_group = 'organizations'
    customer_group = 'customers'

    expert_groups = [expertA_group, expertB_group, expertB_manager_group]

    def __unicode__(self):
        return "%s" % self.user

    class Meta:
        verbose_name = _('user profile')

User.userprofile = property(lambda u: UserProfile.objects.get_or_create(user=u)[0])
User.profile = property(lambda u: UserProfile.objects.get_or_create(user=u)[0])
