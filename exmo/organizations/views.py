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
from datetime import datetime, time

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.forms import TextInput
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import formats
from django.utils.translation import ugettext as _
from django.views.generic import DeleteView, UpdateView

from accounts.forms import SettingsInvCodeForm
from core.helpers import table
from core.views import LoginRequiredMixin
from exmo2010.models import Monitoring, Organization, InviteOrgs, Task, INV_STATUS
from exmo2010.mail import mail_organization
from modeltranslation_utils import CurLocaleModelForm


@login_required
def organization_list(request, monitoring_pk):
    """
    Organization page view.

    """
    name_filter = invite_filter = None
    alert = request.GET.get('alert', False)
    if request.method == "GET":
        name_filter = request.GET.get('name_filter', False)
        invite_filter = request.GET.get('invite_filter', False)

    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    title = _('Organizations for monitoring %s') % monitoring

    all_orgs = Organization.objects.filter(monitoring=monitoring)
    sent = all_orgs.exclude(inv_status='NTS')

    tab = 'all'

    InviteOrgsForm = modelform_factory(InviteOrgs, widgets={'subject': TextInput})
    kwargs = {'instance': InviteOrgs(monitoring=monitoring)}

    if request.method == "POST" and "submit_invite" in request.POST:
        inv_form = InviteOrgsForm(request.POST, **kwargs)
        message = inv_form.data['comment']
        subject = inv_form.data['subject']
        inv_status = inv_form.data['inv_status']
        if inv_form.is_valid():
            inv_form.save()

            if inv_status != 'ALL':
                all_orgs = all_orgs.filter(inv_status=inv_status)

            for org in all_orgs:
                mail_organization(org, subject, message)

            redirect = reverse('exmo2010:organization_list', args=[monitoring_pk]) + "?alert=success#all"
            return HttpResponseRedirect(redirect)
        else:
            alert = 'fail'
    else:
        inv_form = InviteOrgsForm(**kwargs)

    if request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        queryset = Organization.objects.filter(monitoring=monitoring).extra(
            select={
                'task__count': 'SELECT count(*) FROM %s WHERE organization_id = %s.id' % (
                    Task._meta.db_table,
                    Organization._meta.db_table,
                ),
            }
        )

        headers = (
            (_('organization'), 'name', None, None, None),
            (_('email'), 'email', None, None, None),
            (_('phone'), 'phone', None, None, None),
            (_('invitation code'), 'inv_code', None, None, None),
            (_('tasks'), 'task__count', None, None, None),
            (_('invitation'), 'inv_status', None, None, None),
        )
    else:
        org_list = []
        for task in Task.objects.filter(organization__monitoring=monitoring).select_related():
            if request.user.has_perm('exmo2010.view_task', task):
                org_list.append(task.organization.pk)
        org_list = list(set(org_list))
        if not org_list:
            return HttpResponseForbidden(_('Forbidden'))
        queryset = Organization.objects.filter(pk__in=org_list)
        headers = (
            (_('organization'), 'name', None, None, None),
            (_('email'), 'email', None, None, None),
            (_('phone'), 'phone', None, None, None),
            (_('invitation code'), 'inv_code', None, None, None),
            (_('invitation'), 'inv_status', None, None, None),
        )

    if not sent:
        headers_list = list(headers)
        headers_list.pop()
        headers = tuple(headers_list)

    if name_filter:
        queryset = queryset.filter(name__icontains=name_filter)
    if invite_filter and invite_filter != 'ALL':
        queryset = queryset.filter(inv_status=invite_filter)

    OrgForm = modelform_factory(Organization, form=CurLocaleModelForm)

    kwargs = {'instance': Organization(monitoring=monitoring), 'prefix': 'org'}

    if request.method == "POST" and "submit_add" in request.POST:
        form = OrgForm(request.POST, **kwargs)
        if form.is_valid():
            form.save()
        else:
            tab = 'add'
    else:
        form = OrgForm(**kwargs)

    inv_history = InviteOrgs.objects.filter(monitoring=monitoring)

    date_filter_history = None
    invite_filter_history = None

    if request.method == "GET":
        date_filter_history = request.GET.get('date_filter_history', False)
        invite_filter_history = request.GET.get('invite_filter_history', False)

        if date_filter_history:
            input_format = formats.get_format('DATE_INPUT_FORMATS')[0]
            start_datetime = datetime.strptime(date_filter_history, input_format)
            finish_datetime = datetime.combine(start_datetime, time.max)
            inv_history = inv_history.filter(timestamp__range=(start_datetime, finish_datetime))

            tab = 'mail_history'
        if invite_filter_history and invite_filter_history != 'ALL':
            inv_history = inv_history.filter(inv_status=invite_filter_history)
            tab = 'mail_history'

    return table(
        request,
        headers,
        queryset=queryset,
        paginate_by=100,
        template_name='organization_list.html',
        extra_context={
            'title': title,
            'sent': sent,
            'inv_form': inv_form,
            'alert': alert,
            'tab': tab,
            'inv_status': INV_STATUS,
            'monitoring': monitoring,
            'invcodeform': SettingsInvCodeForm(),
            'form': form,
            'inv_history': inv_history,
            'date_filter_history': date_filter_history,
            'invite_filter_history': invite_filter_history,
        },
    )


class OrgMixin(LoginRequiredMixin):
    context_object_name = 'org'

    def get_success_url(self):
        url = reverse('exmo2010:organization_list', args=[self.object.monitoring.pk])
        return '%s?%s' % (url, self.request.GET.urlencode())

    def get_object(self):
        org = get_object_or_404(Organization, pk=self.kwargs['org_pk'])
        if not self.request.user.has_perm('exmo2010.admin_monitoring', org.monitoring):
            raise PermissionDenied
        return org


class OrgEditView(OrgMixin, UpdateView):
    """
    Generic view to edit Organization

    """
    template_name = "edit_organization.html"

    def get_form_class(self):
        return modelform_factory(Organization, form=CurLocaleModelForm)


class OrgDeleteView(OrgMixin, DeleteView):
    template_name = "organization_confirm_delete.html"
