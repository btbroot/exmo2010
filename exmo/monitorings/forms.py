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
from django import forms
from django.utils.translation import ugettext_lazy as _

from core.fields import LocalizeDateInput
from exmo2010.models import Monitoring, MONITORING_PUBLISHED


class MonitoringForm(forms.ModelForm):
    """
    Monitoring form.

    """
    add_questionnaire = forms.BooleanField(required=False, label=_('Add questionnaire'))

    def __init__(self, *args, **kwargs):
        super(MonitoringForm, self).__init__(*args, **kwargs)
        self.fields['rate_date'].required = True
        self.fields['interact_date'].required = True
        self.fields['finishing_date'].required = True
        self.fields['publish_date'].required = True

    class Meta:
        model = Monitoring
        fields = (
            'name',
            'status',
            'openness_expression',
            'map_link',
            'add_questionnaire',
            'no_interact',
            'hidden',
            'rate_date',
            'interact_date',
            'finishing_date',
            'publish_date',
        )
        date_field_attributes = {
            'class': 'datepicker',
            'maxlength': 10,
        }
        widgets = {
            'rate_date': LocalizeDateInput(attrs=date_field_attributes),
            'interact_date': LocalizeDateInput(attrs=date_field_attributes),
            'finishing_date': LocalizeDateInput(attrs=date_field_attributes),
            'publish_date': LocalizeDateInput(attrs=date_field_attributes),
        }


class MonitoringFilterForm(forms.Form):
    """
    Форма выбора мониторинга. К выбору доступны лишь опубликованные.

    """
    monitoring = forms.ModelChoiceField(
        queryset=Monitoring.objects.exclude(hidden=True).filter(
            status=MONITORING_PUBLISHED
        ).order_by('-publish_date'),
        required=False,
        empty_label=_('monitoring not select'),
    )
