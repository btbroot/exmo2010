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

class OrganizationType(models.Model):
  name         = models.CharField(max_length = 255, unique = True)

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)


class Federal(models.Model):
  name         = models.CharField(max_length = 255, unique = True)

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)


class Entity(models.Model):
  name         = models.CharField(max_length = 255, unique = True)
  federal      = models.ForeignKey(Federal)

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)


class Organization(models.Model):
  name         = models.CharField(max_length = 255, unique = True)
  url          = models.URLField(max_length = 255, null = True, blank = True)
  type         = models.ForeignKey(OrganizationType)
  entity       = models.ForeignKey(Entity, null = True, blank = True)
  keywords     = models.TextField(null = True, blank = True)
  comments     = models.TextField(null = True, blank = True)

  def __unicode__(self):
    return '%d. %s' % (self.pk, self.name)

  class Meta:
    ordering = ('id',)


class Category(models.Model):
  code         = models.PositiveIntegerField(unique = True)
  name         = models.CharField(max_length = 255, unique = True)

  def __unicode__(self):
    return '%d. %s' % (self.code, self.name)

  class Meta:
    ordering = ('code',)


class Subcategory(models.Model):
  code         = models.PositiveIntegerField()
  name         = models.CharField(max_length = 255)
  group        = models.ForeignKey(Category)

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
  name               = models.CharField(max_length = 255, unique = True)
  description        = models.TextField(null = True, blank = True)
  complete           = models.BooleanField(default = True)
  topical            = models.BooleanField(default = True)
  accessible         = models.BooleanField(default = True)
  hypertext          = models.BooleanField(default = True)
  document           = models.BooleanField(default = True)
  image              = models.BooleanField(default = True)

  def __unicode__(self):
    return self.name

class Parameter(models.Model):
  code               = models.PositiveIntegerField()
  name               = models.CharField(max_length = 255)
  description        = models.TextField(null = True, blank = True)
  weight             = models.PositiveIntegerField()
  group              = models.ForeignKey(Subcategory)
  type               = models.ForeignKey(ParameterType)
  organizationType   = models.ManyToManyField(OrganizationType)
  exclude            = models.ManyToManyField(Organization, null = True, blank = True)

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


TASK_OPEN       = 0
TASK_READY      = 1
TASK_APPROVED   = 2

class Task(models.Model):
  TASK_STATUS = (
    (TASK_OPEN, _('open')),
    (TASK_READY, _('ready')),
    (TASK_APPROVED, _('approved'))
  )
  user         = models.ForeignKey(User)
  organization = models.ForeignKey(Organization)
  status       = models.PositiveIntegerField(choices = TASK_STATUS)
  c_scores     = '''SELECT COUNT(*)
    FROM exmo2010_Score
    WHERE exmo2010_Score.Task_id = exmo2010_Task.id'''.lower()
  c_parameters = '''SELECT COUNT(*)
    FROM exmo2010_organization JOIN exmo2010_parameter_organizationType
    ON exmo2010_organization.type_id = exmo2010_parameter_organizationType.organizationtype_id
    WHERE exmo2010_organization.id = exmo2010_task.organization_id'''
  c_excludes   = '''SELECT COUNT(*)
    FROM exmo2010_Organization JOIN exmo2010_Parameter_Exclude
    ON exmo2010_Organization.id = exmo2010_Parameter_Exclude.Organization_id
    WHERE exmo2010_Organization.id = exmo2010_Task.Organization_id'''.lower()
  c_complete   = '(%s) * 100 / ((%s) - (%s))' % (c_scores, c_parameters, c_excludes)
  # TODO: Those aggregates shall really filter out "impossible" combinations like an existing Score on an excluded Parameter

  def __unicode__(self):
    return '%s: %s' % (self.user.username, self.organization.name)

  class Meta:
    unique_together = (
      ('user', 'organization'),
    )
    ordering = ('organization__name', 'user__username')


class Score(models.Model):
  task              = models.ForeignKey(Task)
  parameter         = models.ForeignKey(Parameter)
  found             = models.PositiveIntegerField(choices = ((0, 0), (1, 1)))
  complete          = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)))
  completeComment   = models.TextField(null = True, blank = True)
  topical           = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)))
  topicalComment    = models.TextField(null = True, blank = True)
  accessible        = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)))
  accessibleComment = models.TextField(null = True, blank = True)
  hypertext         = models.PositiveIntegerField(null = True, blank = True, choices = ((0, 0), (1, 1)))
  hypertextComment  = models.TextField(null = True, blank = True)
  document          = models.PositiveIntegerField(null = True, blank = True, choices = ((0, 0), (1, 1)))
  documentComment   = models.TextField(null = True, blank = True)
  image             = models.PositiveIntegerField(null = True, blank = True, choices = ((0, 0), (1, 1)))
  imageComment      = models.TextField(null = True, blank = True)
  comment           = models.TextField(null = True, blank = True)

  def __unicode__(self):
    return '%s: %s [%d.%d.%d]' % (
      self.task.user.username,
      self.task.organization.name,
      self.parameter.group.group.code,
      self.parameter.group.code,
      self.parameter.code
    )

  def clean(self):
    from django.core.exceptions import ValidationError
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
        self.complete,
        self.topical,
        self.accessible,
        self.hypertext,
        self.document,
        self.image,
        self.completeComment,
        self.topicalComment,
        self.accessibleComment,
        self.hypertextComment,
        self.documentComment,
        self.imageComment
        )):
      raise ValidationError(_('Not found, but some excessive data persists'))


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

class Feedback(models.Model):
  user          = models.ForeignKey(User)
  score         = models.ForeignKey(Score)
  comment       = models.TextField()
  date          = models.DateTimeField(auto_now = True)
