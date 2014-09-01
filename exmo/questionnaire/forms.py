# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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
from django.utils.translation import ugettext as _


class QuestionnaireDynForm(forms.Form):
    """
    Динамическая форма анкеты с вопросами на странице задачи мониторинга.

    """
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions')
        self.task = kwargs.pop('task', None)
        super(QuestionnaireDynForm, self).__init__(*args, **kwargs)
        for q in questions:
            if q.qtype == 0:
                self.fields['q_%s' % q.pk] = forms.CharField(label=q.question,
                                                             help_text=q.comment, max_length=300, required=False,
                                                             widget=forms.TextInput(attrs={'class': 'name_input',
                                                                                           'placeholder': _('Text')}))
            elif q.qtype == 1:
                self.fields['q_%s' % q.pk] = forms.IntegerField(
                    label=q.question, help_text=q.comment, required=False,
                    widget=forms.TextInput(attrs={'class': 'align-right',
                                                  'placeholder': _('Number')}),
                    min_value=0, max_value=4294967295)
            elif q.qtype == 2:
                self.fields['q_%s' % q.pk] = forms.ModelChoiceField(
                    label=q.question, help_text=q.comment, empty_label=None,
                    required=False,
                    queryset=q.answervariant_set.order_by('-pk'),
                    widget=forms.RadioSelect())

    def clean(self):
        cleaned_data = self.cleaned_data
        for answ in cleaned_data.items():
            if answ[0].startswith("q_") and not answ[1] and self.task and self.task.approved:
                raise forms.ValidationError(_('Answer cannot be deleted for approved task. Edit answer instead.'))
        return cleaned_data
