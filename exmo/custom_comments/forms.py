# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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

from django.utils.translation import ugettext_lazy as _
from django import forms
from django.contrib.comments.forms import CommentDetailsForm

class CustomCommentDetailsForm(CommentDetailsForm):
    def check_for_duplicate_comment(self, new):
        """
        Check that a submitted comment isn't a duplicate.
        Overridden function to allow duplicates.
        """
        # проверяет дубликаты комментарие,
        # в оргинальной функции возвращает старый коментарий,
        # если он повторяется. Перекрыто,
        # чтобы пользователи могли оставлять повторяющиеся комментарии
        return new

class CustomCommentForm(CustomCommentDetailsForm):
    honeypot      = forms.CharField(required=False,
        label=_('If you enter anything in this field '\
                'your comment will be treated as spam'))

    def clean_honeypot(self):
        """Check that nothing's been entered into the honeypot."""
        value = self.cleaned_data["honeypot"]
        if value:
            raise forms.ValidationError(self.fields["honeypot"].label)
        return value