# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
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

from queryform import QueryForm
from exmo2010.models.organization import INV_STATUS


class OrganizationsQueryForm(QueryForm):
    INV_STATUS_FILTER = [('', _('All invitations'))] + INV_STATUS

    org_name = forms.CharField(required=False,
                               widget=forms.TextInput(attrs={'placeholder': _('Organization')}))
    inv_status = forms.ChoiceField(required=False, choices=INV_STATUS_FILTER)

    class Meta:
        filters = {
            'org_name': 'name__icontains',
            'inv_status': 'inv_status',
        }
        order = {
            'org_name': 'name',
            'email': 'email',
            'phone': 'phone',
            'inv_code': 'inv_code',
            'tasks_count': 'tasks_count',
            'inv_status': 'inv_status',
        }


class RepresentativesQueryForm(QueryForm):
    full_name_or_email = forms.CharField(required=False,
                                         widget=forms.TextInput(attrs={'placeholder': _('Full name or e-mail')}))
    organization = forms.ChoiceField(required=False)

    class Meta:
        distinct = True
        filters = {
            'full_name_or_email': [
                'user__first_name__icontains',
                'user__last_name__icontains',
                'user__email__icontains'
            ],
            'organization': 'organization__pk',
        }

    def __init__(self, monitoring, *args, **kwargs):
        super(RepresentativesQueryForm, self).__init__(*args, **kwargs)

        orgs = monitoring.organization_set.exclude(userprofile=None).order_by('name')
        org_choices = [('', _('Organization is not selected'))] + list(orgs.values_list('pk', 'name'))
        self.fields['organization'].choices = org_choices
