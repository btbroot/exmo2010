# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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
from django_select2.fields import ModelSelect2Field

from exmo2010.models import Parameter
from queryform import QueryForm


class ParamCritScoreFilterForm(forms.Form):
    """
    Форма фильтрации оценок по параметру и значениям критериев.
    Кроме стандартных вариантов оценок у критерия, добавляем вариант 5,
    означающий, что ничего не выбрано и фильтрация по этому критерию не нужна.

    """
    _01 = ((5, "-"), (0, "0"), (1, "1"))
    _123 = ((5, "-"), (1, "1"), (2, "2"), (3, "3"))

    parameter = ModelSelect2Field(label=_('Parameter'), queryset=None, empty_label="")

    found = forms.ChoiceField(label=_('Found'), choices=_01, initial=5, widget=forms.RadioSelect)
    complete = forms.ChoiceField(label=_('Complete'), choices=_123, initial=5, widget=forms.RadioSelect)
    topical = forms.ChoiceField(label=_('Topical'), choices=_123, initial=5, widget=forms.RadioSelect)
    accessible = forms.ChoiceField(label=_('Accessible'), choices=_123, initial=5, widget=forms.RadioSelect)
    hypertext = forms.ChoiceField(label=_('Hypertext'), choices=_01, initial=5, widget=forms.RadioSelect)
    document = forms.ChoiceField(label=_('Document'), choices=_01, initial=5, widget=forms.RadioSelect)
    image = forms.ChoiceField(label=_('Image'), choices=_01, initial=5, widget=forms.RadioSelect)

    t_opened = forms.BooleanField(label=_('opened'), required=False, initial=True)
    t_closed = forms.BooleanField(label=_('closed'), required=False, initial=True)
    t_approved = forms.BooleanField(label=_('approved'), required=False, initial=True)

    def __init__(self, *args, **kwargs):
        monitoring = kwargs.pop('monitoring', None)
        super(ParamCritScoreFilterForm, self).__init__(*args, **kwargs)
        self.fields['parameter'].queryset = Parameter.objects.filter(monitoring=monitoring).order_by('code')
        self.fields['parameter'].label_from_instance = lambda param: u"%s — %s" % (param.code, param.name)

    def criteria_fields(self):
        yield self['found']
        for criterion in Parameter.OPTIONAL_CRITERIA:
            yield self[criterion]


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


class ParametersQueryForm(QueryForm):
    name = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': _('Parameter')}))

    class Meta:
        filters = {
            'name': 'name__icontains',
        }
