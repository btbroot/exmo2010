from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
  name         = models.CharField(max_length = 200, unique = True)
  url          = models.CharField(max_length = 200, unique = True)

  def __unicode__(self):
    return self.name


class Category(models.Model):
  code         = models.IntegerField(unique = True)
  name         = models.CharField(max_length = 200, unique = True)

  def __unicode__(self):
    return '%d. %s' % (self.code, self.name)

  class Meta:
    ordering = ('code',)


class Subcategory(models.Model):
  code         = models.IntegerField()
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
  code         = models.IntegerField()
  name         = models.CharField(max_length = 200)
  description  = models.CharField(max_length = 1024)
  group        = models.ForeignKey(Subcategory)
  weight       = models.IntegerField()

  def __unicode__(self):
    return '%d.%d.%d. %s' % (self.group.group.code, self.group.code, self.code, self.name)

  class Meta:
    unique_together = (
      ('name', 'group'),
      ('code', 'group'),
    )
    ordering = ('group__group__code', 'group__code', 'code')
    permissions = (
      ('can_change_own_score', 'Can change own score'),
    )


class Criteria(models.Model):
  code         = models.CharField(max_length = 2, unique = True)
  name         = models.CharField(max_length = 20, unique = True)
  minimum      = models.IntegerField()
  maximum      = models.IntegerField()

  def __unicode__(self):
    return self.name


class Score(models.Model):
  organization = models.ForeignKey(Organization)
  parameter    = models.ForeignKey(Parameter)
  criteria     = models.ForeignKey(Criteria)
  score        = models.IntegerField(null = True, blank = True)
  author       = models.ForeignKey(User, null = True, blank = True)

  class Meta:
    unique_together = (
      ('organization', 'parameter', 'criteria', 'author'),
    )
