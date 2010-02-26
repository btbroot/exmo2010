from django.db import models
from django.contrib.auth.models import User


class OrganizationType(models.Model):
  name         = models.CharField(max_length = 200, unique = True)

  def __unicode__(self):
    return self.name

  class Meta:
    ordering = ('name',)


class Organization(models.Model):
  name         = models.CharField(max_length = 200, unique = True)
  url          = models.URLField(max_length = 200, unique = True)
  type         = models.ForeignKey(OrganizationType)
  comments     = models.TextField(null = True, blank = True,)

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


class Score(models.Model):
  organization = models.ForeignKey(Organization)
  parameter    = models.ForeignKey(Parameter)
  required     = models.BooleanField(default = True)
  found        = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2)))
  complete     = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)))
  topical      = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)))
  accessible   = models.PositiveIntegerField(null = True, blank = True, choices = ((1, 1), (2, 2), (3, 3)))
  comments     = models.TextField(null = True, blank = True,)
  user         = models.ForeignKey(User, null = True)

  def __unicode__(self):
    return '%s [%d.%d.%d]' % (self.organization.name, self.parameter.group.group.code, self.parameter.group.code, self.parameter.code)

  class Meta:
    unique_together = (
      ('organization', 'parameter'),
    )
    ordering = ('organization', 'parameter')