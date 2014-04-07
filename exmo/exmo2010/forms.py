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
from django.conf import settings
from django.forms.widgets import Textarea
from django.utils import formats
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from core.utils import clean_message

DATETIME_INPUT_FORMATS = list(formats.get_format('DATETIME_INPUT_FORMATS')) + ['%d.%m.%Y %H:%M:%S']

# основные JS ресурсы для форм с виджетами из админки
CORE_JS = (
    settings.STATIC_URL + 'admin/js/core.js',
    settings.STATIC_URL + 'admin/js/admin/RelatedObjectLookups.js',
    settings.STATIC_URL + 'exmo2010/js/jquery/jquery.min.js',
    settings.STATIC_URL + 'admin/js/jquery.init.js',
    settings.STATIC_URL + 'admin/js/actions.min.js',
)

CORE_MEDIA = forms.Media(js=CORE_JS)


class HorizRadioRenderer(forms.RadioSelect.renderer):
    """ this overrides widget method to put radio buttons horizontally
        instead of vertically.
    """
    def render(self):
        """Outputs radios"""
        return mark_safe(u'\n'.join([u'%s\n' % w for w in self]))


class EmailReadonlyWidget(forms.Widget):
    def render(self, name, value=" ", attrs=None):
        html = '<p id="id_%(name)s" name="%(name)s">%(value)s</p>' % \
               {'name': name, 'value': value}
        return mark_safe(html)


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
