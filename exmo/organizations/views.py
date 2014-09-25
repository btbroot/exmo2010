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
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.forms.models import modelform_factory
from django.forms import TextInput
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import formats
from django.utils.translation import ugettext as _
from django.views.generic import DeleteView, DetailView, UpdateView

from .forms import OrganizationsQueryForm, RepresentativesQueryForm
from accounts.forms import SettingsInvCodeForm
from core.helpers import table
from core.views import LoginRequiredMixin
from core.utils import UnicodeWriter
from exmo2010.mail import mail_organization
from exmo2010.models import (LicenseTextFragments, Monitoring, Organization,
                             InviteOrgs, Score, Task, UserProfile, INV_STATUS)
from modeltranslation_utils import CurLocaleModelForm


@login_required
def organization_list(request, monitoring_pk):
    """
    Organization page view.

    """
    alert = request.GET.get('alert', False)

    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        raise PermissionDenied
    title = _('Organizations for monitoring %s') % monitoring

    all_orgs = Organization.objects.filter(monitoring=monitoring)

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

    headers = (
        (_('organization'), 'name', None, None, None),
        (_('email'), 'email', None, None, None),
        (_('phone'), 'phone', None, None, None),
        (_('invitation code'), 'inv_code', None, None, None),
        (_('tasks'), 'task__count', None, None, None),
        (_('status'), 'inv_status', None, None, None),
    )

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
            inv_history = inv_history.filter(timestamp__gte=start_datetime)

            tab = 'mail_history'
        if invite_filter_history and invite_filter_history != 'ALL':
            inv_history = inv_history.filter(inv_status=invite_filter_history)
            tab = 'mail_history'

    queryset = Organization.objects.filter(monitoring=monitoring).annotate(tasks_count=Count('task'))

    org_queryform = OrganizationsQueryForm(request.GET)
    if org_queryform.is_valid():
        queryset = org_queryform.apply(queryset)

    return table(
        request,
        headers,
        queryset=queryset,
        paginate_by=100,
        template_name='organization_list.html',
        extra_context={
            'title': title,
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
            'org_queryform': org_queryform,
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


def _add_comments_count(user, orgs):
    scores = Score.objects.filter(task__organization__in=orgs)
    comments_count = user.user.comment_comments.filter(object_pk__in=scores).count()
    user.comments_count = comments_count
    return


class RepresentativesView(LoginRequiredMixin, DetailView):
    template_name = "organization_representatives.html"
    pk_url_kwarg = 'monitoring_pk'
    model = Monitoring

    def get_object(self, queryset=None):
        obj = super(RepresentativesView, self).get_object(queryset)
        if not self.request.user.has_perm('exmo2010.admin_monitoring', obj):
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        context = super(RepresentativesView, self).get_context_data(**kwargs)

        orgs = self.object.organization_set.exclude(userprofile=None).order_by('name')
        users = UserProfile.objects.filter(user__groups__name='organizations', organization__monitoring=self.object)
        representatives_exist = users.exists()

        queryform = RepresentativesQueryForm(self.request.GET)
        org_choices = [('', _('Organization is not selected'))] + list(orgs.values_list('pk', 'name'))
        queryform.fields['organizations'].choices = org_choices

        if queryform.is_valid():
            users = queryform.apply(users)
            org_pk = queryform.cleaned_data['organizations']
            if org_pk:
                orgs = orgs.filter(pk=org_pk)

        users = set(users.values_list('pk', flat=True))

        organizations = []
        for org in orgs:
            orgusers = []
            for user in sorted(org.userprofile_set.all(),  key=lambda m: m.full_name):
                if user.pk in users:
                    _add_comments_count(user, orgs)
                    orgusers.append(user)

            if orgusers:
                org.users = orgusers
                organizations.append(org)

        context['orgs'] = organizations
        context['representatives_exist'] = representatives_exist
        context['queryform'] = queryform

        return context


def representatives_export(request, monitoring_pk):
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        raise PermissionDenied

    orgs = monitoring.organization_set.order_by('name')

    organizations = []
    for org in orgs:
        orgusers = []
        for user in sorted(org.userprofile_set.all(),  key=lambda m: m.full_name):
            _add_comments_count(user, orgs)
            orgusers.append(user)

        org.users = orgusers
        organizations.append(org)

    response = HttpResponse(mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=representatives-%s.csv' % monitoring_pk
    response.encoding = 'UTF-16'
    writer = UnicodeWriter(response)
    writer.writerow([
        '#Verified',
        'Organization',
        'First name',
        'Last name',
        'Email',
        'Phone',
        'Job title',
        'Comments count',
        'Date joined',
    ])

    for org in organizations:
        for user in org.users:
            row = [
                int(user.user.is_active),
                org.name,
                user.user.first_name,
                user.user.last_name,
                user.user.email,
                user.phone,
                user.position,
                user.comments_count,
                user.user.date_joined.date().isoformat(),
            ]
            writer.writerow(row)

    license = LicenseTextFragments.objects.filter(pk='license')
    if license:
        writer.writerow([u'#%s' % license[0].csv_footer])

    return response
