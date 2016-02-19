# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2015 IRSI LTD
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


class FeedbackItem(BaseModel):
    class Meta(BaseModel.Meta):
        verbose_name = _('Feedback item')
        verbose_name_plural = _('Feedback items')

    header = models.TextField(verbose_name=_('header'))
    text = RichTextField(verbose_name=_('text'))
    scanned_image = models.ImageField(upload_to='feedback/scanned/', verbose_name=_('scanned image'), max_length=255)
    emblem = models.ImageField(upload_to='feedback/emblems/', verbose_name=_('emblem'), max_length=255)
    created = models.DateTimeField(verbose_name=_('creation time'))

    def __unicode__(self):
        return u'%s (%s object)' % (self.header, self.__class__.__name__)
