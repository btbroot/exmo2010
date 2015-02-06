# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2015 IRSI LTD
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
from django.contrib.auth.models import User
from django.forms import Form, ModelChoiceField, ModelMultipleChoiceField
from django.utils.translation import ugettext_lazy as _

from exmo2010.forms import FilteredSelectMultiple
from exmo2010.models import Organization


class MassAssignmentTasksForm(Form):
    expert = ModelChoiceField(label=_('Expert'), empty_label=_('Not selected'),
                              queryset=User.objects.filter(is_active=True, groups__name='expertsB'))
    organizations = ModelMultipleChoiceField(label=_('Organizations'), queryset=None,
                                             widget=FilteredSelectMultiple('', is_stacked=False))

    def __init__(self, *args, **kwargs):
        monitoring = kwargs.pop('monitoring', None)
        super(MassAssignmentTasksForm, self).__init__(*args, **kwargs)
        self.fields['organizations'].queryset = Organization.objects.filter(monitoring=monitoring, task__isnull=True)
        self.fields['expert'].label_from_instance = lambda u: u'%s' % u.userprofile.full_name
