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
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .base import BaseModel


class LicenseTextFragments(BaseModel):
    """
    Model for simple text fragments editable by staff.
    LicenseTextFragments is identified by its name as primary key,
    for example: "license".

    """
    class Meta(BaseModel.Meta):
        verbose_name = _('License text fragment')
        verbose_name_plural = _('License text fragments')

    id = models.CharField(max_length=255, primary_key=True, verbose_name=_('identifier'))
    page_footer = models.TextField(default='', blank=True, verbose_name=_('page footer'))
    csv_footer = models.TextField(default='', blank=True, verbose_name=_('csv footer'))
    json_name = models.CharField(max_length=255, default='', blank=True, verbose_name=_('json name'))
    json_url = models.URLField(max_length=255, default='', blank=True, verbose_name=_('json url'))
    json_rightsholder = models.URLField(max_length=255, default='', blank=True, verbose_name=_('json rightsholder'))
    json_source = models.URLField(max_length=255, default='', blank=True, verbose_name=_('json source'))

    def __unicode__(self):
        return u'%s (%s object)' % (self.id, self.__class__.__name__)

    @property
    def json_license(self):
        result = {}
        if self.json_name:
            result.update({'name': self.json_name})
        if self.json_url:
            result.update({'url': self.json_url})
        if self.json_rightsholder:
            result.update({'rightsholder': self.json_rightsholder})
        if self.json_source:
            result.update({'source': self.json_source})

        return result
