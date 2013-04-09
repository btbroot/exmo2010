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

from exmo2010.models import Score


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
            'foundComment': forms.Textarea(attrs={'cols': 45, 'rows': 1}),
            'completeComment': forms.Textarea(attrs={'cols': 45, 'rows': 1}),
            'topicalComment': forms.Textarea(attrs={'cols': 45, 'rows': 1}),
            'accessibleComment': forms.Textarea(attrs={'cols': 45, 'rows': 1}),
            'documentComment': forms.Textarea(attrs={'cols': 45, 'rows': 1}),
            'hypertextComment': forms.Textarea(attrs={'cols': 45, 'rows': 1}),
            'imageComment': forms.Textarea(attrs={'cols': 45, 'rows': 1}),
            'comment': forms.Textarea(attrs={'cols': 45, 'rows': 5}),
        }
        exclude = ('revision',)
