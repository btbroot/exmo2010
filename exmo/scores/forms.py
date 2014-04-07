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
from ckeditor.widgets import CKEditorWidget
from django import forms
from django.contrib.comments.forms import COMMENT_MAX_LENGTH
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext, ugettext_lazy as _

from custom_comments.forms import CustomCommentForm
from exmo2010.models import Parameter, Score


class ScoreForm(forms.ModelForm):
    """
    Форма выставления оценки.

    """
    def __init__(self, *args, **kwargs):
        super(ScoreForm, self).__init__(*args, **kwargs)
        # префикс для формы, чтобы в верстке поле id_comment не пересекалось
        # с полем комментариев, т.к. по id wyswyg-редактор цепляется к форме
        self.prefix = "score"
        # Замена "-----" на "-" в виджетах полей формы варианта blank choice
        fields_to_change = ('found', 'complete', 'topical', 'accessible',
                            'document', 'hypertext', 'image')
        for f in fields_to_change:
            self.fields[f].widget.choices[0] = ('', '-')

    class Meta:
        model = Score
        widgets = {
            'found': forms.RadioSelect(),
            'complete': forms.RadioSelect(),
            'topical': forms.RadioSelect(),
            'accessible': forms.RadioSelect(),
            'document': forms.RadioSelect(),
            'hypertext': forms.RadioSelect(),
            'image': forms.RadioSelect(),
            'comment': forms.Textarea(attrs={'cols': 45, 'rows': 5}),
            'revision': forms.HiddenInput(),
        }


class ScoreFormWithComment(CustomCommentForm):
    # options for radio buttons (variant of scores):
    BASE_CHOICE = (('', '-'), (0, 0), (1, 1))
    FULL_CHOICE = (('', '-'), (1, 1), (2, 2), (3, 3))

    def __init__(self, instance=None, **kwargs):
        super(ScoreFormWithComment, self).__init__(instance, **kwargs)

    found = forms.ChoiceField(label=_('found'), widget=forms.RadioSelect(), choices=BASE_CHOICE)
    complete = forms.ChoiceField(label=_('complete'), widget=forms.RadioSelect(), choices=FULL_CHOICE, required=False)
    topical = forms.ChoiceField(label=_('topical'), widget=forms.RadioSelect(), choices=FULL_CHOICE, required=False)
    accessible = forms.ChoiceField(label=_('accessible'), widget=forms.RadioSelect(), choices=FULL_CHOICE, required=False)
    hypertext = forms.ChoiceField(label=_('hypertext'), widget=forms.RadioSelect(), choices=BASE_CHOICE, required=False)
    document = forms.ChoiceField(label=_('document'), widget=forms.RadioSelect(), choices=BASE_CHOICE, required=False)
    image = forms.ChoiceField(label=_('image'), widget=forms.RadioSelect(), choices=BASE_CHOICE, required=False)
    recomendation = forms.CharField(label=_('recommendations'), widget=forms.Textarea(), required=False)
    comment = forms.CharField(label=_('comment'), widget=CKEditorWidget(config_name='simplified'),
                              max_length=COMMENT_MAX_LENGTH, required=False)

    # overwrite method from CustomCommentForm
    def get_comment_create_data(self):
        result = super(CustomCommentForm, self).get_comment_create_data()

        return result

    def clean_comment(self):
        comment = self.cleaned_data['comment']
        if comment:
            comment = super(ScoreFormWithComment, self).clean_comment()

        return comment

    def clean(self):
        def _checker(criterion):
            if getattr(obj.parameter, criterion) and data[criterion] in ('', None):
                raise ValidationError(ugettext('%s must be set' % criterion.capitalize()))

        data = self.cleaned_data
        obj = self.target_object

        if 'found' not in data:
            raise ValidationError(ugettext('Found must be set'))

        if int(data['found']):
            for item in Parameter.OPTIONAL_CRITERIONS:
                _checker(item)
        elif any((
            bool(data['complete']),
            bool(data['topical']),
            bool(data['accessible']),
            bool(data['hypertext']),
            bool(data['document']),
            bool(data['image']),
        )):
            raise ValidationError(ugettext('Not found, but some excessive data persists'))

        return super(ScoreFormWithComment, self).clean()

    def save(self):
        data = self.cleaned_data
        score = Score.objects.get(pk=data['object_pk'])

        for item in ['found'] + Parameter.OPTIONAL_CRITERIONS:
            setattr(score, item, data[item] if data[item] else None)

        if 'recomendation' in data:
            score.comment = data['recomendation']

        score.save()

        return score
