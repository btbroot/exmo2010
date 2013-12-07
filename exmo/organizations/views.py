# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
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
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ProcessFormView, ModelFormMixin

from accounts.forms import SettingsInvCodeForm
from core.helpers import table
from exmo2010.models import Monitoring, Organization, InviteOrgs, Task, INV_STATUS
from organizations.forms import OrganizationForm, InviteOrgsForm
from organizations.tasks import send_org_email


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

    initial = {'monitoring': monitoring}

    tab = 'all'

    if request.method == "POST" and "submit_invite" in request.POST:
        inv_form = InviteOrgsForm(request.POST)
        comment = inv_form.data['comment']
        subject = inv_form.data['subject']
        inv_status = inv_form.data['inv_status']
        if inv_form.is_valid():
            inv_form.save()

            if inv_status != 'ALL':
                all_orgs = all_orgs.filter(inv_status=inv_status)

            for org in all_orgs:
                message = comment.replace('%code%', org.inv_code)
                context = {
                    'subject': subject,
                    'message': message
                }
                if org.email:
                    emails = filter(None, org.email.split(', '))
                else:
                    continue
                send_org_email.delay(emails, subject, 'organizations/invitation_email', org.pk, context)

            redirect = reverse('exmo2010:organization_list', args=[monitoring_pk])+"?alert=success#all"
            return HttpResponseRedirect(redirect)
        else:
            initial.update({'comment': comment, 'inv_status': inv_status})
            alert = 'fail'
    else:
        inv_form = InviteOrgsForm(initial=initial)

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

    initial = {'monitoring': monitoring}
    form = OrganizationForm(initial=initial)
    if request.method == "POST" and "submit_add" in request.POST:
        form = OrganizationForm(request.POST)
        if form.is_valid():
            form.save()
            form = OrganizationForm(initial=initial)
        else:
            tab = 'add'

    inv_history = InviteOrgs.objects.filter(monitoring=monitoring)

    date_filter_history = None
    invite_filter_history = None

    if request.method == "GET":
        date_filter_history = request.GET.get('date_filter_history', False)
        invite_filter_history = request.GET.get('invite_filter_history', False)

        if date_filter_history:
            start_datetime = datetime.strptime("%s 00:00:00" % date_filter_history, '%d.%m.%Y %H:%M:%S')
            finish_datetime = datetime.strptime("%s 23:59:59" % date_filter_history, '%d.%m.%Y %H:%M:%S')
            inv_history = inv_history.filter(timestamp__gt=start_datetime,
                                             timestamp__lt=finish_datetime)
            tab = 'mail_history'
        if invite_filter_history and invite_filter_history != 'ALL':
            inv_history = inv_history.filter(inv_status=invite_filter_history)
            tab = 'mail_history'

    return table(
        request,
        headers,
        queryset=queryset,
        paginate_by=100,
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


class OrganizationManagerView(SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):
    """
    Generic view to edit or delete monitoring
    """
    model = Organization
    form_class = OrganizationForm
    template_name = "exmo2010/organization_form.html"
    context_object_name = "object"
    extra_context = {}
    pk_url_kwarg = 'org_pk'

    def add(self, request, monitoring):
        self.object = None
        title = _('Add new organization for %s') % monitoring
        self.extra_context = {
            'title': title,
            'tab': 'add',
            'monitoring': monitoring
        }

    def update(self, request, monitoring):
        self.object = self.get_object()
        title = _('Edit organization %s') % monitoring
        self.extra_context = {
            'title': title,
            'monitoring': monitoring
        }

    def get_redirect(self, request, monitoring):
        redirect = '%s?%s' % (reverse('exmo2010:organization_list', args=[monitoring.pk]), request.GET.urlencode())
        redirect = redirect.replace("%", "%%")
        return redirect

    def get_context_data(self, **kwargs):
        context = super(OrganizationManagerView, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

    def get(self, request, *args, **kwargs):
        monitoring = get_object_or_404(Monitoring, pk=self.kwargs["monitoring_pk"])
        if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        self.success_url = self.get_redirect(request, monitoring)
        self.initial = {'monitoring': monitoring}

        if self.kwargs["method"] == 'add':
            self.add(request, monitoring)

        if self.kwargs["method"] == 'delete':
            self.object = self.get_object()
            self.template_name = "exmo2010/organization_confirm_delete.html"
            title = _('Delete organization %s') % monitoring
            self.extra_context = {
                'title': title,
                'monitoring': monitoring,
                'deleted_objects': Task.objects.filter(organization=self.object)
            }
        if self.kwargs["method"] == 'update':
            self.update(request, monitoring)

        return super(OrganizationManagerView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        monitoring = get_object_or_404(Monitoring, pk=self.kwargs["monitoring_pk"])
        if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        self.success_url = self.get_redirect(request, monitoring)
        if self.kwargs["method"] == 'add':
            self.add(request, monitoring)
            return super(OrganizationManagerView, self).post(request, *args, **kwargs)
        if self.kwargs["method"] == 'delete':
            self.object = self.get_object()
            self.object.delete()
            return HttpResponseRedirect(self.get_success_url())
        elif self.kwargs["method"] == 'update':
            self.update(request, monitoring)
            return super(OrganizationManagerView, self).post(request, *args, **kwargs)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(OrganizationManagerView, self).dispatch(*args, **kwargs)
