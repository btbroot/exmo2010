# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2016 IRSI LTD
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
from django.db.models import DateTimeField, ForeignKey, TextField, CharField, BooleanField
from django.utils.translation import pgettext, pgettext_lazy, ugettext_lazy as _

from .base import BaseModel
from .organization import INV_STATUS_ALL


class SentMailHistory(BaseModel):
    """
    Sent email history.

    """
    timestamp = DateTimeField(auto_now_add=True, verbose_name=_('date and time'), editable=False)
    monitoring = ForeignKey("Monitoring", verbose_name=_('monitoring'), editable=False)
    subject = TextField(verbose_name=_('subject'))
    comment = RichTextField(config_name='advanced', verbose_name=_('Letter content'))
    inv_status = CharField(
        max_length=3, choices=INV_STATUS_ALL, default='ALL', verbose_name=_('Invitation status'))

    dst_orgs_noreg = BooleanField(default=False, verbose_name=pgettext_lazy(u'(organizations)', u'Not registered'))
    dst_orgs_inact = BooleanField(default=False, verbose_name=pgettext_lazy(u'(organizations)', u'Inactive'))
    dst_orgs_activ = BooleanField(default=False, verbose_name=pgettext_lazy(u'(organizations)', u'Active'))

    dst_orgusers_inact = BooleanField(default=False, verbose_name=pgettext_lazy(u'(representatives)', u'Inactive'))
    dst_orgusers_activ = BooleanField(default=False, verbose_name=pgettext_lazy(u'(representatives)', u'Active'))
    dst_orgusers_unseen = BooleanField(default=False, verbose_name=pgettext_lazy(u'(representatives)', u'Proto'))

    def dst_orgs_display(self):
        """
        Get human-readable state of dst_orgs_* fields. Used in mail history template.
        """
        if self.dst_orgs_noreg and self.dst_orgs_inact and self.dst_orgs_activ:
            return pgettext(u'(organizations)', u'All')
        else:
            verbose_names = []
            for attr in ['dst_orgs_noreg', 'dst_orgs_inact', 'dst_orgs_activ']:
                if getattr(self, attr):
                    verbose_names.append(unicode(self._meta.get_field(attr).verbose_name))
            return ', '.join(verbose_names)

    def dst_orgusers_display(self):
        """
        Get human-readable state of dst_orgusers_* fields. Used in mail history template.
        """
        if self.dst_orgusers_inact and self.dst_orgusers_activ and self.dst_orgusers_unseen:
            return pgettext(u'(representatives)', u'All')
        else:
            verbose_names = []
            for attr in ['dst_orgusers_inact', 'dst_orgusers_activ', 'dst_orgusers_unseen']:
                if getattr(self, attr):
                    verbose_names.append(unicode(self._meta.get_field(attr).verbose_name))
            return ', '.join(verbose_names)

    def clean(self):
        fields = [
            'dst_orgs_noreg',
            'dst_orgs_inact',
            'dst_orgs_activ',
            'dst_orgusers_inact',
            'dst_orgusers_activ',
            'dst_orgusers_unseen']
        if not any(getattr(self, attr) for attr in fields):
            raise ValidationError(_(u'Message should have destination organizations or representatives'))
