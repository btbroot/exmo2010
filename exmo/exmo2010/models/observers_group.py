# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
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
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import pgettext_lazy, ugettext_lazy as _

from .base import BaseModel


class ObserversGroup(BaseModel):

    class Meta(BaseModel.Meta):
        verbose_name = pgettext_lazy(u'change observer in admin', u'Observers group')
        verbose_name_plural = _('Observers groups')
        ordering = ('name',)

    name = models.CharField(max_length=255, verbose_name=_('group name'))
    monitoring = models.ForeignKey("Monitoring", verbose_name=_('monitoring'))
    organizations = models.ManyToManyField("Organization", null=True, blank=True, verbose_name=_('organizations'))
    users = models.ManyToManyField(User, null=True, blank=True, verbose_name=_('users'))

    def __unicode__(self):
        return self.name
