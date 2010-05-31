from django.db import models
from django.contrib.auth.models import User


class OrganizationType(models.Model):
  name         = models.CharField(max_length = 200, unique = True)

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)


class Federal(models.Model):
  name         = models.CharField(max_length = 200, unique = True)

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)


class Entity(models.Model):
  name         = models.CharField(max_length = 200, unique = True)
  federal      = models.ForeignKey(Federal)

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)


class Organization(models.Model):
  name         = models.CharField(max_length = 200, unique = True)
  url          = models.URLField(max_length = 200, unique = True)
  type         = models.ForeignKey(OrganizationType)
  entity       = models.ForeignKey(Entity, null = True, blank = True)
  keywords     = models.CharField(max_length = 200, null = True, blank = True)
  comments     = models.TextField(null = True, blank = True)

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)


class Category(models.Model):
  code         = models.PositiveIntegerField(unique = True)
  name         = models.CharField(max_length = 200, unique = True)

  def __unicode__(self):
    return '%d. %s' % (self.code, self.name)

  class Meta:
    ordering = ('code',)


class Subcategory(models.Model):
  code         = models.PositiveIntegerField()
  name         = models.CharField(max_length = 200)
  group        = models.ForeignKey(Category)

  def __unicode__(self):
    return '%d.%d. %s' % (self.group.code, self.code, self.name)

  class Meta:
    unique_together = (
      ('name', 'group'),
      ('code', 'group'),
    )
    ordering = ('group__code', 'code')


class Parameter(models.Model):
  code               = models.PositiveIntegerField()
  name               = models.CharField(max_length = 200)
  description        = models.TextField(null = True, blank = True)
  group              = models.ForeignKey(Subcategory)
  type               = models.ManyToManyField(OrganizationType)
  exclude            = models.ManyToManyField(Organization)
  weight             = models.PositiveIntegerField()
  completeRequired   = models.BooleanField(default = True)
  topicalRequired    = models.BooleanField(default = True)
  accessibleRequired = models.BooleanField(default = True)

  def __unicode__(self):
    return '%d.%d.%d. %s' % (self.group.group.code, self.group.code, self.code, self.name)

  class Meta:
    unique_together = (
      ('name', 'group'),
      ('code', 'group'),
    )
    ordering = ('group__group__code', 'group__code', 'code')


class Task(models.Model):
  user         = models.ForeignKey(User)
  organization = models.ForeignKey(Organization)
  open         = models.BooleanField()

  def __unicode__(self):
    return '%s: %s' % (self.user.username, self.organization.name)

  class Meta:
    unique_together = (
      ('user', 'organization'),
    )
    ordering = ('user__username', 'organization__name')


class Score(models.Model):
  task         = models.ForeignKey(Task)
  parameter    = models.ForeignKey(Parameter)
  found        = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2)))
  complete     = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)))
  completeComment = models.TextField(null = True, blank = True)
  topical      = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)))
  topicalComment = models.TextField(null = True, blank = True)
  accessible   = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)))
  assessibleComment = models.TextField(null = True, blank = True)
  comment      = models.TextField(null = True, blank = True)

  def __unicode__(self):
    return '%s: %s [%d.%d.%d]' % (self.task.user.username, self.task.organization.name, self.parameter.group.group.code, self.parameter.group.code, self.parameter.code)

  class Meta:
    unique_together = (
      ('task', 'parameter'),
    )
    ordering = ('task__user__username', 'task__organization__name', 'parameter__group__group__code', 'parameter__group__code', 'parameter__code')

