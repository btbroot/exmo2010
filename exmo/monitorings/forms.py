# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
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
from django.conf import settings
from django.utils.translation import ugettext as _

from exmo2010.models import Monitoring, MONITORING_STATUS, MONITORING_PUBLISHED


class MonitoringForm(forms.ModelForm):
    """
    Форма редактирования/создания мониторинга.

    """
    status = forms.ChoiceField(choices=MONITORING_STATUS,
                               label=_('Status'))
    add_questionnaire = forms.BooleanField(required=False,
                                           label=_('Add questionnaire'))

    def __init__(self, *args, **kwargs):
        super(MonitoringForm, self).__init__(*args, **kwargs)
        self.fields['rate_date'].required = True
        self.fields['interact_date'].required = True
        self.fields['finishing_date'].required = True
        self.fields['publish_date'].required = True
        self.fields.keyOrder = [
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
        ]

    class Meta:
        model = Monitoring
        exclude = ('time_to_answer',
                   'prepare_date',
                   'result_date',
                   )
        widgets = {
            'rate_date': forms.DateInput(attrs={
                'class': 'jdatefield',
                'maxlength': 300
            }),
            'interact_date': forms.DateInput(attrs={
                'class': 'jdatefield',
                'maxlength': 300
            }),
            'finishing_date': forms.DateInput(attrs={
                'class': 'jdatefield',
                'maxlength': 300
            }),
            'publish_date': forms.DateInput(attrs={
                'class': 'jdatefield',
                'maxlength': 300
            }),
        }

    class Media:
        css = {
            'all': (
                settings.STATIC_URL + 'exmo2010/css/jquery-ui.css',
            )
        }
        js = (
            settings.STATIC_URL + 'exmo2010/js/jquery/jquery.min.js',
            settings.STATIC_URL + 'exmo2010/js/jquery/jquery-ui.min.js',
        )


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


class TableSettingsForm(forms.Form):
    representatives = forms.BooleanField(required=False, label=_('Representatives'))
    comment_quantity = forms.BooleanField(required=False, label=_('Comment quantity'))
    initial_openness = forms.BooleanField(required=False, label=_('Initial openness'))
    final_openness = forms.BooleanField(required=False, label=_('Final Openness'))
    difference = forms.BooleanField(required=False, label=_('Difference'))




