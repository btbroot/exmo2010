# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2016 IRSI LTD
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
from django.forms import BooleanField, CharField, CheckboxSelectMultiple, MultipleChoiceField, TextInput
from django.utils.translation import ugettext_lazy as _

from exmo2010.models import Monitoring
from modeltranslation_utils import CurLocaleModelForm
from queryform import QueryForm


class MonitoringCopyForm(CurLocaleModelForm):
    # FIXME: `name` field is missing on copy page because CurLocaleModelForm currently only
    # reliably works when used dynamically as base in modelform_facory. Using it like this,
    # as base of custom declared class will fail if modeltranslation routines was not run
    # before the Modelform metaclass.

    class Meta:
        model = Monitoring
        exclude = ['time_to_answer', 'map_link']

    DONORS = (
        ('all', _('All')),
        ('organizations', _('Organizations')),
        ('parameters', _('Parameters')),
        ('tasks', _('Tasks list')),
        ('all_scores', _('All scores')),
        ('current_scores', _('Current scores')),
        ('representatives', _('Representatives')),
    )
    add_questionnaire = BooleanField(required=False, label=_('Monitoring cycle with questionnaire'))
    donors = MultipleChoiceField(required=False, label=_('What to copy?'),
                                 choices=DONORS, widget=CheckboxSelectMultiple)

    def clean_donors(self):
        """
        :return: valid list of 'donors' field options
        """
        donors = set(self.cleaned_data['donors'])
        if not {'parameters', 'tasks'}.issubset(donors):
            donors -= {'all_scores', 'current_scores'}

        return donors


class MonitoringsQueryForm(QueryForm):
    name = CharField(required=False, widget=TextInput(attrs={'placeholder': _('Monitoring cycle')}))

    class Meta:
        filters = {
            'name': 'name__icontains',
        }


class RatingsQueryForm(QueryForm):
    name = CharField(required=False, widget=TextInput(attrs={'placeholder': _('Monitoring cycle')}))

    class Meta:
        filters = {
            'name': 'name__icontains',
        }


class RatingQueryForm(QueryForm):
    name = CharField(required=False, widget=TextInput(attrs={'placeholder': _('Organization')}))

    class Meta:
        filters = {
            'name': 'name__icontains',
        }


class ObserversGroupQueryForm(QueryForm):
    name = CharField(required=False, widget=TextInput(attrs={'placeholder': _('Group name')}))

    class Meta:
        filters = {
            'name': 'name__icontains',
        }
