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
from ckeditor.widgets import CKEditorWidget
from django import forms
from django.contrib.admin import widgets as admin_widgets
from django.forms.widgets import Textarea, Media
from django.utils.translation import ugettext_lazy as _

from core.utils import clean_message
from queryform import QueryForm


class FeedbackForm(forms.Form):
    email = forms.EmailField(label=_("E-mail"), required=True)
    comment = forms.CharField(widget=CKEditorWidget(config_name='simplified'), label=_('Your problem'), required=True)

    def clean_comment(self):
        return clean_message(self.cleaned_data['comment'])


class CertificateOrderForm(forms.Form):
    ADDRESSEE_CHOICES = (('org', _('to organization')), ('user', _('to employee')))
    DELIVERY_METHOD_CHOICES = (('email', _('by email')), ('post', _('by post')))

    task_id = forms.IntegerField()
    rating_type = forms.ChoiceField(choices=zip(* [('all', 'npa', 'other')] * 2), initial='all', required=False)
    addressee = forms.ChoiceField(label=_('Certificate for'), choices=ADDRESSEE_CHOICES,
                                  widget=forms.RadioSelect(), initial='org', required=False)
    delivery_method = forms.ChoiceField(label=_('Send'), choices=DELIVERY_METHOD_CHOICES, widget=forms.RadioSelect(),
                                        initial='email', required=False)
    name = forms.CharField(label=_('Name'), max_length=100, required=False)
    wishes = forms.CharField(label=_('Wishes'), widget=Textarea(), required=False)
    email = forms.EmailField(label=_('Email'), max_length=100, required=False)
    for_whom = forms.CharField(label=_('For whom'), max_length=100, required=False)
    zip_code = forms.CharField(label=_('Zip code'), max_length=6, min_length=6, required=False)
    address = forms.CharField(label=_('Address'), widget=Textarea(), required=False)

    def full_clean(self):
        '''
        Determine required fields from 'addressee' and 'delivery_method' values
        '''
        if self._raw_value('delivery_method') == 'post':
            self.fields['for_whom'].required = True
            self.fields['zip_code'].required = True
            self.fields['address'].required = True
        else:
            self.fields['email'].required = True

        if self._raw_value('addressee') == 'user':
            self.fields['name'].required = True

        return super(CertificateOrderForm, self).full_clean()


class CertificateOrderQueryForm(QueryForm):
    name_filter = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': _('Organization')}))

    class Meta:
        filters = {
            'name_filter': 'name__icontains',
        }


class FilteredSelectMultiple(admin_widgets.FilteredSelectMultiple):
    """
    Extended widget from contrib.admin.
    Django admin uses scripts with built-in jquery which is initialized once in admin-related template.
    Outside of admin templates we have to add this initialization js scripts as media in this extended widget
    in addition to the original scripts.
    Plus we have some css customization.
    """
    @property
    def media(self):
        admin_js = 'jquery.min.js jquery.init.js core.js SelectBox.js SelectFilter2.js'.split()
        css = {"all": ["admin/css/forms.css", "exmo2010/css/selector.css"]}
        return Media(css=css, js=["admin/js/%s" % path for path in admin_js])
