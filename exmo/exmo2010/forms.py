# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2015 IRSI LTD
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
from django.contrib.admin import widgets as admin_widgets
from django.db.models import Q
from django.forms import Form, CharField, ChoiceField, EmailField, IntegerField
from django.forms.widgets import Textarea, TextInput, RadioSelect, Media
from django.utils.translation import ugettext_lazy as _

from core.utils import clean_message
from queryform import QueryForm
from .models import Task, Monitoring
from .models.monitoring import RATE, RES, INT, FIN


class FeedbackForm(Form):
    email = EmailField(label=_("E-mail"), required=True)
    comment = CharField(widget=CKEditorWidget(config_name='simplified'), label=_('Your problem'), required=True)

    def clean_comment(self):
        return clean_message(self.cleaned_data['comment'])


class CertificateOrderForm(Form):
    ADDRESSEE_CHOICES = (('org', _('to organization')), ('user', _('to employee')))
    DELIVERY_METHOD_CHOICES = (('email', _('by email')), ('post', _('by post')))
    RATING_TYPE_CHOICES = (('all', 'all'), ('npa', 'npa'), ('other', 'other'))

    task_id = IntegerField()
    rating_type = ChoiceField(choices=RATING_TYPE_CHOICES, initial='all', required=False)
    name = CharField(label=_('Name'), max_length=100, required=False)
    wishes = CharField(label=_('Wishes'), widget=Textarea(), required=False)
    email = EmailField(label=_('Email'), max_length=100, required=False)
    for_whom = CharField(label=_('For whom'), max_length=100, required=False)
    zip_code = CharField(label=_('Zip code'), max_length=6, min_length=6, required=False)
    address = CharField(label=_('Address'), widget=Textarea(), required=False)
    addressee = ChoiceField(
        label=_('Certificate for'), choices=ADDRESSEE_CHOICES, widget=RadioSelect(), initial='org', required=False)
    delivery_method = ChoiceField(
        label=_('Send'), choices=DELIVERY_METHOD_CHOICES, widget=RadioSelect(), initial='email', required=False)

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
    name_filter = CharField(required=False, widget=TextInput(attrs={'placeholder': _('Organization')}))

    class Meta:
        filters = {
            'name_filter': 'name__icontains',
        }


class TasksIndexQueryForm(QueryForm):
    TASK_STATUS_CHOICES = [('', _('Any status'))] + list(Task.TASK_STATUS)

    org_name = CharField(required=False, widget=TextInput(attrs={'placeholder': _('Organization')}))
    task_status = ChoiceField(required=False, choices=TASK_STATUS_CHOICES)
    monitoring = ChoiceField(required=False)

    class Meta:
        filters = {
            'org_name': 'organization__name__icontains',
            'task_status': 'status',
            'monitoring': 'organization__monitoring__pk',
        }

    def __init__(self, analyst, *args, **kwargs):
        super(TasksIndexQueryForm, self).__init__(*args, **kwargs)

        filter = Q(organization__task__user=analyst, status__in=[RATE, RES, INT, FIN])
        monitorings = Monitoring.objects.filter(filter).order_by('publish_date').distinct()
        choices = [('', _('Any monitoring'))] + list(monitorings.values_list('pk', 'name'))
        self.fields['monitoring'].choices = choices


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
