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
from ckeditor.fields import RichTextField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .base import BaseModel


class StaticPage(BaseModel):
    """
    Model for simple web pages editable by staff. View and url should be added statically.
    StaticPage is identified by its name as primary key, for example: "help", "about".
    """
    id = models.CharField(max_length=255, primary_key=True, verbose_name=_('identifier'))
    description = models.TextField(default='', blank=True, verbose_name=_('description'))
    content = RichTextField(default='', blank=True, verbose_name=_('content'))

    def __unicode__(self):
        return u'%s (%s)' % (self.id, self.description)
