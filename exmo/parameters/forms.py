# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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
from django.contrib.admin import widgets
from django.utils.translation import ugettext as _

from exmo2010.forms import TagAutocomplete
from exmo2010.models import Organization, Parameter


SCORE_CHOICES1 = (
    (5, "-"),
    (0, "0"),
    (1, "1"),
)

SCORE_CHOICES2 = (
    (5, "-"),
    (1, "1"),
    (2, "2"),
    (3, "3"),
)


class ParamCritScoreFilterForm(forms.Form):
    """
    Форма фильтрации оценок по параметру и значениям критериев.
    Кроме стандартных вариантов оценок у критерия, добавляем вариант 5,
    означающий, что ничего не выбрано и фильтрация по этому критерию не нужна.

    """
    parameter = forms.ModelChoiceField(label=_('Parameter'),
                                       queryset=Parameter.objects.none(), empty_label="")
    found = forms.ChoiceField(label=_('Found'), choices=SCORE_CHOICES1,
                              initial=5, widget=forms.RadioSelect)
    complete = forms.ChoiceField(label=_('Complete'), choices=SCORE_CHOICES2,
                                 initial=5, widget=forms.RadioSelect)
    topical = forms.ChoiceField(label=_('Topical'), choices=SCORE_CHOICES2,
                                initial=5, widget=forms.RadioSelect)
    accessible = forms.ChoiceField(label=_('Accessible'),
                                   choices=SCORE_CHOICES2, initial=5, widget=forms.RadioSelect)
    hypertext = forms.ChoiceField(label=_('Hypertext'), choices=SCORE_CHOICES1,
                                  initial=5, widget=forms.RadioSelect)
    document = forms.ChoiceField(label=_('Document'), choices=SCORE_CHOICES1,
                                 initial=5, widget=forms.RadioSelect)
    image = forms.ChoiceField(label=_('Image'), choices=SCORE_CHOICES1,
                              initial=5, widget=forms.RadioSelect)
    t_opened = forms.BooleanField(label=_('opened'), required=False,
                                  initial=True)
    t_closed = forms.BooleanField(label=_('closed'), required=False,
                                  initial=True)
    t_approved = forms.BooleanField(label=_('approved'), required=False,
                                    initial=True)

    def __init__(self, *args, **kwargs):
        monitoring = kwargs.pop('monitoring', None)
        super(ParamCritScoreFilterForm, self).__init__(*args, **kwargs)
        self.fields['parameter'].queryset = Parameter.objects.filter(
            monitoring=monitoring)


class ParameterForm(forms.ModelForm):
    """
    Форма редактирования/создания параметра.

    """
    def __init__(self, *args, **kwargs):
        """
        Фильтруем организации для поля exclude
        """
        _parameter = kwargs.get('instance')
        _monitoring = kwargs.get('monitoring')
        if _monitoring:
            kwargs.pop('monitoring')
        super(ParameterForm, self).__init__(*args, **kwargs)
        if _parameter:
            self.fields['exclude'].queryset = Organization.objects.filter(monitoring=_parameter.monitoring)
        if _monitoring:
            self.fields['exclude'].queryset = Organization.objects.filter(monitoring=_monitoring)
            self.fields['monitoring'].initial = _monitoring

    class Meta:
        model = Parameter
        widgets = {
            'keywords': TagAutocomplete,
            'exclude': widgets.FilteredSelectMultiple('', is_stacked=False),
            'monitoring': forms.widgets.HiddenInput,
        }

    class Media:
        css = {
            "all": ("exmo2010/selector.css",)
        }


class ParameterTypeForm(forms.ModelForm):
    """
    Форма для использования в формсете
    на странице установки типа параметра.

    """
    class Meta:
        model = Parameter
        fields = ('npa',)

    def __init__(self, *args, **kwargs):
        super(ParameterTypeForm, self).__init__(*args, **kwargs)
        self.fields['npa'].label = self.instance.name


class ParameterDynForm(forms.Form):
    """
    Динамическая форма параметров мониторинга.

    """
    def __init__(self, *args, **kwargs):
        monitoring = kwargs.pop('monitoring')
        super(ParameterDynForm, self).__init__(*args, **kwargs)
        for p in Parameter.objects.filter(monitoring=monitoring):
            self.fields['parameter_%s' % p.pk] = forms.BooleanField(label=p.name,
                                                                    help_text=p.description,
                                                                    required=False,
                                                                    )
