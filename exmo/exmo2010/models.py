from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
  name         = models.CharField(max_length = 200, unique = True)
  url          = models.CharField(max_length = 200)

  def __unicode__(self):
    return self.name


class Parameter(models.Model):
  name         = models.CharField(max_length = 200, unique = True)
  shortName    = models.CharField(max_length = 10)
  weight       = models.IntegerField()

  def __unicode__(self):
    return '%s. %s' % (self.shortName, self.name)


class Quality(models.Model):
  name         = models.CharField(max_length = 200, unique = True)

  def __unicode__(self):
    return self.name


class Score(models.Model):
  organization = models.ForeignKey(Organization)
  parameter    = models.ForeignKey(Parameter)
  quality      = models.ForeignKey(Quality)
  score        = models.IntegerField(null = True)
  author       = models.ForeignKey(User)
  
  class Meta:
    unique_together = (
      ('organization', 'parameter', 'quality', 'author'),
    )