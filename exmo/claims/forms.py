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
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from core.utils import urlize, sanitize_field


class ClaimAddForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea, label=_('Your claim'))
    claim_id = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput())

    def clean_comment(self):
        data = self.cleaned_data['comment']
        data = sanitize_field(data)
        data = urlize(data)
        return data


class ClaimReportForm(forms.Form):
    """
    Форма для отчета по претензиям.

    """
    creator = forms.ChoiceField()
    addressee = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        creator_id_list = kwargs.pop("creator_id_list")
        addressee_id_list = kwargs.pop("addressee_id_list")
        super(ClaimReportForm, self).__init__(*args, **kwargs)
        creator_choices = [(0, _("all managers"))]
        for i in creator_id_list:
            user = User.objects.get(pk=i)
            name = user.profile.legal_name
            creator_choices.append((i, name))
        self.fields['creator'].choices = creator_choices
        addressee_choices = [(0, _("all experts"))]
        for i in addressee_id_list:
            user = User.objects.get(pk=i)
            name = user.profile.legal_name
            addressee_choices.append((i, name))
        self.fields['addressee'].choices = addressee_choices
