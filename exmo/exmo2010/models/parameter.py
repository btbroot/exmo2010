# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .base import BaseModel


class Parameter(BaseModel):
    """Параметр."""

    class Meta(BaseModel.Meta):
        ordering = ('code', 'name')
        unique_together = (
            ('code', 'monitoring'),
            ('name', 'monitoring'),
        )

    code = models.PositiveIntegerField(verbose_name=_('code'))
    name = models.CharField(max_length=1000, verbose_name=_('name'))
    description = RichTextField(blank=True, verbose_name=_('description'))
    monitoring = models.ForeignKey("Monitoring", verbose_name=_('monitoring'), editable=False)
    exclude = models.ManyToManyField("Organization", null=True, blank=True, verbose_name=_('excluded organizations'))
    weight = models.IntegerField(verbose_name=_('weight'))

    complete = models.BooleanField(default=True, verbose_name=_('complete'))
    topical = models.BooleanField(default=True, verbose_name=_('topical'))
    accessible = models.BooleanField(default=True, verbose_name=_('accessible'))
    hypertext = models.BooleanField(default=True, verbose_name=_('hypertext'))
    document = models.BooleanField(default=True, verbose_name=_('document'))
    image = models.BooleanField(default=True, verbose_name=_('image'))
    npa = models.BooleanField(default=False, verbose_name=_('normative parameter'))

    #необязательные критерии в оценке
    OPTIONAL_CRITERIONS = [
        'complete',
        'topical',
        'accessible',
        'hypertext',
        'document',
        'image'
    ]

    def __unicode__(self):
        return self.name

    def clean(self):
        result = super(Parameter, self).clean()
        try:
            self.validate_unique()
        except ValidationError, e:
            raise ValidationError(e.update_error_dict({}))

        return result
