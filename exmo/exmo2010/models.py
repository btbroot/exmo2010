# This file is part of EXMO2010 software.
# Copyright 2010 Al Nikolov
# Copyright 2010 Institute for Information Freedom Development
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



class OrganizationType(models.Model):
  name         = models.CharField(max_length = 255, unique = True, verbose_name=_('name'))

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)



class Federal(models.Model):
  name         = models.CharField(max_length = 255, unique = True, verbose_name=_('name'))

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)



class Entity(models.Model):
  name         = models.CharField(max_length = 255, unique = True, verbose_name=_('name'))
  federal      = models.ForeignKey(Federal, verbose_name=_('federal'))

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)



class Organization(models.Model):
  '''
  name -- Uniq organization name
  url -- Internet site URL
  type -- Type of organization (FOIV, ROIV, ROIZ, etc)
  entity -- Federal district for organization (if organization not federal)
  keywords -- Keywords for autocomplete and search
  comments -- Additional comment
  keyname -- Field identifies the group name from auth.models.Group model. Maxlength for auth.models.Group is 30, so this field also have, max_length = 30
  '''

  name         = models.CharField(max_length = 255, unique = True, verbose_name=_('name'))
  url          = models.URLField(max_length = 255, null = True, blank = True, verbose_name=_('url'))
  type         = models.ForeignKey(OrganizationType, verbose_name=_('organization type'))
  entity       = models.ForeignKey(Entity, null = True, blank = True, verbose_name=_('entity'))
  keywords     = models.TextField(null = True, blank = True, verbose_name=_('keywords'))
  comments     = models.TextField(null = True, blank = True, verbose_name=_('comments'))
  keyname      = models.CharField(max_length = 30, unique = True, verbose_name=_('keyname'))

  def __unicode__(self):
    return '%s' % (self.name)

  class Meta:
    ordering = ('name',)



class Category(models.Model):
  code         = models.PositiveIntegerField(unique = True, verbose_name=_('code'))
  name         = models.CharField(max_length = 255, unique = True, verbose_name=_('name'))

  def __unicode__(self):
    return '%d. %s' % (self.code, self.name)

  class Meta:
    ordering = ('code',)



class Subcategory(models.Model):
  code         = models.PositiveIntegerField(verbose_name=_('code'))
  name         = models.CharField(max_length = 255, verbose_name=_('name'))
  group        = models.ForeignKey(Category, verbose_name=_('category'))

  def __unicode__(self):
    return '%d.%d. %s' % (self.group.code, self.code, self.name)

  def fullcode(self):
    return '%d.%d' % (self.group.code, self.code)

  class Meta:
    unique_together = (
      ('name', 'group'),
      ('code', 'group'),
    )
    ordering = ('group__code', 'code')



class ParameterType(models.Model):
  name               = models.CharField(max_length = 255, unique = True, verbose_name=_('name'))
  description        = models.TextField(null = True, blank = True, verbose_name=_('description'))
  complete           = models.BooleanField(default = True, verbose_name=_('complete'))
  topical            = models.BooleanField(default = True, verbose_name=_('topical'))
  accessible         = models.BooleanField(default = True, verbose_name=_('accessible'))
  hypertext          = models.BooleanField(default = True, verbose_name=_('hypertext'))
  document           = models.BooleanField(default = True, verbose_name=_('document'))
  image              = models.BooleanField(default = True, verbose_name=_('image'))

  def __unicode__(self):
    return self.name



class Monitoring(models.Model):
  name               = models.CharField(max_length = 255, default = "-", verbose_name=_('name'))
  type               = models.ForeignKey(OrganizationType, verbose_name=_('organization type'))

  def __unicode__(self):
    return '%s: %s' % (self.type.name, self.name)

  class Meta:
    unique_together = (('name', 'type'))
    ordering = ('type__name', 'name')



class Parameter(models.Model):
  code               = models.PositiveIntegerField(verbose_name=_('code'))
  name               = models.CharField(max_length = 255, verbose_name=_('name'))
  description        = models.TextField(null = True, blank = True, verbose_name=_('description'))
  group              = models.ForeignKey(Subcategory, verbose_name=_('subcategory'))
  type               = models.ForeignKey(ParameterType, verbose_name=_('parameter type'))
  monitoring         = models.ManyToManyField(Monitoring, verbose_name=_('monitoring'), through='ParameterMonitoringProperty')
  exclude            = models.ManyToManyField(Organization, null = True, blank = True, verbose_name=_('excluded organizations'))

  def __unicode__(self):
    return '%d.%d.%d. %s' % (self.group.group.code, self.group.code, self.code, self.name)

  def fullcode(self):
    return '%d.%d.%d' % (self.group.group.code, self.group.code, self.code)

  class Meta:
    unique_together = (
      ('name', 'group'),
      ('code', 'group'),
    )
    ordering = ('group__group__code', 'group__code', 'code')



class ParameterMonitoringProperty(models.Model):
  monitoring = models.ForeignKey(Monitoring)
  parameter  = models.ForeignKey(Parameter)
  weight     = models.IntegerField(verbose_name=_('weight'))

  class Meta:
    unique_together = (
      ('monitoring', 'parameter'),
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
  TASK_READY      = 1
  TASK_APPROVED   = 2
  TASK_STATUS     = (
    (TASK_OPEN, _('opened')),
    (TASK_READY, _('ready')),
    (TASK_APPROVED, _('approved'))
  )
  user         = models.ForeignKey(User, verbose_name=_('user'))
  organization = models.ForeignKey(Organization, verbose_name=_('organization'))
  monitoring   = models.ForeignKey(Monitoring, verbose_name=_('monitoring'))
  status       = models.PositiveIntegerField(choices = TASK_STATUS, verbose_name=_('status'))
  _scores_invalid = '''
    FROM exmo2010_Score
    JOIN exmo2010_Parameter ON exmo2010_Score.parameter_id = exmo2010_Parameter.id
    JOIN exmo2010_Parameter_Exclude ON exmo2010_Parameter.id = exmo2010_Parameter_Exclude.parameter_id
    WHERE exmo2010_Parameter_Exclude.organization_id = exmo2010_Task.Organization_id
    '''.lower()
  _scores = '''
    FROM exmo2010_Score
    JOIN exmo2010_Parameter ON exmo2010_Score.parameter_id = exmo2010_Parameter.id
    JOIN exmo2010_ParameterType ON exmo2010_Parameter.type_id = exmo2010_ParameterType.id
    JOIN exmo2010_ParameterMonitoringProperty ON exmo2010_Parameter.id = exmo2010_ParameterMonitoringProperty.parameter_id
    WHERE exmo2010_ParameterMonitoringProperty.monitoring_id = exmo2010_Task.monitoring_id
    AND exmo2010_Score.Task_id = exmo2010_Task.id
    AND exmo2010_Score.id NOT IN (SELECT exmo2010_Score.id %s)
    '''.lower() % _scores_invalid
  _parameters_invalid = '''
    FROM exmo2010_Parameter_Exclude
    WHERE exmo2010_Parameter_Exclude.Organization_id = exmo2010_Task.Organization_id
    '''.lower()
  _parameters = '''
    FROM exmo2010_Parameter
    INNER JOIN exmo2010_ParameterMonitoringProperty ON exmo2010_Parameter.id = exmo2010_ParameterMonitoringProperty.parameter_id
    WHERE exmo2010_ParameterMonitoringProperty.monitoring_id = exmo2010_Task.monitoring_id
    AND NOT (exmo2010_Parameter.id IN (SELECT exmo2010_Parameter_Exclude.parameter_id %s) AND NOT (exmo2010_Parameter.id IS NULL))
    '''.lower() % _parameters_invalid
  _complete   = '((SELECT COUNT(*) %s) * 100 / (SELECT COUNT(*) %s))'.lower() % (_scores, _parameters)
  _openness_max = 'SELECT SUM(exmo2010_ParameterMonitoringProperty.weight) %s AND exmo2010_ParameterMonitoringProperty.weight > 0'.lower() % _parameters
  _score_value = '''
    exmo2010_ParameterMonitoringProperty.weight *
    exmo2010_Score.found *
    CASE exmo2010_ParameterType.complete
      WHEN 0 THEN 1 ELSE
      CASE exmo2010_Score.complete
        WHEN 1 THEN 0.2
        WHEN 2 THEN 0.5
        WHEN 3 THEN 1
      END
    END *
    CASE exmo2010_ParameterType.topical
      WHEN 0 THEN 1 ELSE
      CASE exmo2010_Score.topical
        WHEN 1 THEN 0.7
        WHEN 2 THEN 0.85
        WHEN 3 THEN 1
      END
    END *
    CASE exmo2010_ParameterType.accessible
      WHEN 0 THEN 1 ELSE
      CASE exmo2010_Score.accessible
        WHEN 1 THEN 0.9
        WHEN 2 THEN 0.95
        WHEN 3 THEN 1
      END
    END *
    CASE exmo2010_ParameterType.hypertext
      WHEN 0 THEN 1 ELSE
      CASE exmo2010_ParameterType.document
        WHEN 0 THEN
          CASE exmo2010_Score.hypertext
            WHEN 0 THEN 0.2
            WHEN 1 THEN 1
          END ELSE
          CASE exmo2010_Score.hypertext
            WHEN 0 THEN
              CASE exmo2010_Score.document
                WHEN 0 THEN 0.2
                WHEN 1 THEN 0.2
              END
            WHEN 1 THEN
              CASE exmo2010_Score.document
                WHEN 0 THEN 0.9
                WHEN 1 THEN 1
              END
          END
      END
    END
  '''.lower()
  _openness_actual = 'SELECT SUM(%s) %s' % (_score_value, _scores)
  _openness = '((%s) * 100 / (%s))' % (_openness_actual, _openness_max)

  def openness(self):
    scores = Score.objects.filter(task = self, parameter__in = Parameter.objects.filter(monitoring = self.monitoring)).exclude(parameter__exclude = self.organization).extra(
        select={'weight': 'select weight from %s where monitoring_id=%s and parameter_id=%s.id' % (ParameterMonitoringProperty._meta.db_table, self.monitoring.pk, Parameter._meta.db_table)})
    openness_actual = sum([openness_helper(s,s.weight) for s in scores])
    parameters_weight = Parameter.objects.exclude(exclude = self.organization).filter(monitoring = self.monitoring, parametermonitoringproperty__weight__gte = 0).extra(
        select={'weight': 'select weight from %s where monitoring_id=%s and parameter_id=%s.id' % (ParameterMonitoringProperty._meta.db_table, self.monitoring.pk, Parameter._meta.db_table)})
    openness_max = sum([parameter_weight.weight for parameter_weight in parameters_weight])
    openness = float(openness_actual * 100) / openness_max
    return openness

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
      ('user', 'organization', 'monitoring'),
    )
    ordering = ('monitoring__name', 'organization__name', 'user__username')

  def clean(self):
    if self.organization.type != self.monitoring.type:
        raise ValidationError(_('Ambigous organization type.'))
    if self.ready or self.approved:
        complete = Task.objects.extra(select = {'complete': Task._complete}).get(pk = self.pk).complete
        if complete != 100:
            raise ValidationError(_('Ready task must be 100% complete.'))

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

  def _set_ready(self ,val):
    if val:
        self.status = self.TASK_READY

  def _set_approved(self, val):
    if val:
        self.status = self.TASK_APPROVED

  open = property(_get_open, _set_open)
  ready = property(_get_ready, _set_ready)
  approved = property(_get_approved, _set_approved)



class Score(models.Model):
  CLAIM_NEVER = 0
  CLAIM_NO = 1
  CLAIM_YES = 2
  CLAIM_STATUS = (
    (CLAIM_NEVER, _('never')),
    (CLAIM_YES, _('yes')),
    (CLAIM_NO, _('no')),
  )
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
  claim             = models.IntegerField(choices = CLAIM_STATUS, default = CLAIM_NEVER, verbose_name=_('claim'))

  def __unicode__(self):
    return '%s: %s [%d.%d.%d]' % (
      self.task.user.username,
      self.task.organization.name,
      self.parameter.group.group.code,
      self.parameter.group.code,
      self.parameter.code
    )

  def clean(self):
    if self.found:
      if self.parameter.type.complete   and self.complete   in ('', None):
        raise ValidationError(_('Complete must be set'))
      if self.parameter.type.topical    and self.topical    in ('', None):
        raise ValidationError(_('Topical must be set'))
      if self.parameter.type.accessible and self.accessible in ('', None):
        raise ValidationError(_('Accessible must be set'))
      if self.parameter.type.hypertext  and self.hypertext  in ('', None):
        raise ValidationError(_('Hypertext must be set'))
      if self.parameter.type.document   and self.document   in ('', None):
        raise ValidationError(_('Document must be set'))
      if self.parameter.type.image      and self.image      in ('', None):
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
    if self.claim == self.CLAIM_YES:
        return True
    else: return False

  def _set_claim(self, val):
    if val:
        self.claim = self.CLAIM_YES
    else:
        self.claim = self.CLAIM_NO

  def openness(self):
    try:
        weight = ParameterMonitoringProperty.objects.get(parameter = self.parameter, monitoring = self.task.monitoring).weight
    except:
        return 0
    return openness_helper(self, weight)

  active_claim = property(_get_claim, _set_claim)

  class Meta:
    unique_together = (
      ('task', 'parameter'),
    )
    ordering = (
      'task__user__username',
      'task__organization__name',
      'parameter__group__group__code',
      'parameter__group__code',
      'parameter__code'
    )



def openness_helper(score, weight_in=0):
    try:
        weight = score.weight
    except:
        weight = weight_in

    found = score.found
    complete = 1
    topical = 1
    accessible = 1
    format = 1
    if score.parameter.type.complete:
        if score.complete == 1: complete = 0.2
        if score.complete == 2: complete = 0.5
        if score.complete == 3: complete = 1
    if score.parameter.type.topical:
        if score.topical == 1: topical = 0.7
        if score.topical == 2: topical = 0.85
        if score.topical == 3: topical = 1
    if score.parameter.type.accessible:
        if score.accessible == 1: accessible = 0.9
        if score.accessible == 2: accessible = 0.95
        if score.accessible == 3: accessible = 1
    if score.parameter.type.hypertext:
        if score.parameter.type.document:
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
