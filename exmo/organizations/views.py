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
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.forms.models import modelform_factory
from django.forms import TextInput
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import DeleteView, DetailView, UpdateView

from .forms import InviteOrgsQueryForm, OrganizationsQueryForm, RepresentativesQueryForm
from core.views import LoginRequiredMixin
from core.utils import UnicodeWriter
from exmo2010.mail import mail_organization, mail_orguser
from exmo2010.models import LicenseTextFragments, Monitoring, Organization, InviteOrgs, Score, UserProfile
from modeltranslation_utils import CurLocaleModelForm


class OrganizationsView(LoginRequiredMixin, DetailView):
    template_name = "organizations.html"
    pk_url_kwarg = 'monitoring_pk'
    model = Monitoring

    def get_object(self, queryset=None):
        monitoring = super(OrganizationsView, self).get_object(queryset)
        if not self.request.user.has_perm('exmo2010.admin_monitoring', monitoring):
            raise PermissionDenied
        return monitoring

    def get_context_data(self, **kwargs):
        context = super(OrganizationsView, self).get_context_data(**kwargs)

        organizations = Organization.objects.filter(monitoring=self.object).annotate(tasks_count=Count('task'))
        context['is_organizations_exists'] = organizations.exists()

        queryform = OrganizationsQueryForm(self.request.GET)
        if queryform.is_valid():
            organizations = queryform.apply(organizations)

        context['organizations'] = organizations
        context['queryform'] = queryform

        return context


class OrganizationsMixin(LoginRequiredMixin):
    context_object_name = 'org'

    def get_context_data(self, **kwargs):
        context = super(OrganizationsMixin, self).get_context_data(**kwargs)
        context['monitoring'] = self.monitoring
        return context

    def get_success_url(self):
        url = reverse('exmo2010:organizations', args=[self.object.monitoring.pk])
        return '%s?%s' % (url, self.request.GET.urlencode())


class OrganizationsEditView(OrganizationsMixin, UpdateView):
    template_name = "organizations_edit.html"

    def get_object(self, queryset=None):
        if 'org_pk' in self.kwargs:
            # Existing organization edit page
            org = get_object_or_404(Organization, pk=self.kwargs['org_pk'])
            self.monitoring = org.monitoring
        else:
            # New organization page
            self.monitoring = get_object_or_404(Monitoring, pk=self.kwargs['monitoring_pk'])
            org = Organization(monitoring=self.monitoring)

        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return org

    def get_form_class(self):
        return modelform_factory(Organization, form=CurLocaleModelForm)


class OrganizationsDeleteView(OrganizationsMixin, DeleteView):
    template_name = "organizations_delete.html"

    def get_object(self, queryset=None):
        org = get_object_or_404(Organization, pk=self.kwargs['org_pk'])
        self.monitoring = org.monitoring

        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return org


class SendMailMixin(LoginRequiredMixin):
    pk_url_kwarg = 'monitoring_pk'
    context_object_name = 'monitoring'
    model = Monitoring

    def get_object(self, queryset=None):
        self.monitoring = super(SendMailMixin, self).get_object(queryset)
        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return self.monitoring


class SendMailView(SendMailMixin, UpdateView):
    template_name = "send_mail.html"

    def get_form_class(self):
        return modelform_factory(InviteOrgs, exclude=('monitoring', 'inv_status'), widgets={'subject': TextInput})

    def get_form_kwargs(self):
        kwargs = super(SendMailView, self).get_form_kwargs()
        kwargs.update({'instance': InviteOrgs(monitoring=self.monitoring)})
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        formdata = form.cleaned_data

        orgs = []
        if formdata.get('dst_orgs_noreg'):
            orgs += self.monitoring.organization_set.filter(inv_status__in=['NTS', 'SNT', 'RD'])
        if formdata.get('dst_orgs_inact'):
            orgs += self.monitoring.organization_set.filter(inv_status='RGS')
        if formdata.get('dst_orgs_activ'):
            orgs += self.monitoring.organization_set.filter(inv_status='ACT')

        for org in orgs:
            mail_organization(org, formdata['subject'], formdata['comment'])

        orgs = set(self.monitoring.organization_set.all())

        orgusers = UserProfile.objects.filter(organization__monitoring=self.monitoring).prefetch_related('organization')
        scores = Score.objects.filter(parameter__monitoring=self.monitoring)
        active = orgusers.filter(user__comment_comments__object_pk__in=scores).distinct()
        inactive = orgusers.exclude(user__comment_comments__object_pk__in=scores).distinct()

        if formdata.get('dst_orgusers_inact'):
            for user in inactive:
                if '%code%' in formdata['comment']:
                    # Send email to this user for every related org in this monitoring, expanding %code%
                    for org in filter(orgs.__contains__, user.organization.all()):
                        mail_orguser(user.user, org.inv_code, formdata['subject'], formdata['comment'])
                else:
                    # Send single email to this user.
                    mail_orguser(user.user, '', formdata['subject'], formdata['comment'])

        if formdata.get('dst_orgusers_activ'):
            for user in active:
                if '%code%' in formdata['comment']:
                    # Send email to this user for every related org in this monitoring, expanding %code%
                    for org in filter(orgs.__contains__, user.organization.all()):
                        mail_orguser(user.user, org.inv_code, formdata['subject'], formdata['comment'])
                else:
                    # Send single email to this user.
                    mail_orguser(user.user, '', formdata['subject'], formdata['comment'])

        messages.success(self.request, _('Mails sent.'))
        url = reverse('exmo2010:organizations', args=[self.monitoring.pk])

        return HttpResponseRedirect('%s?%s' % (url, self.request.GET.urlencode()))


class SendMailHistoryView(SendMailMixin, DetailView):
    template_name = "send_mail_history.html"

    def get_context_data(self, **kwargs):
        context = super(SendMailHistoryView, self).get_context_data(**kwargs)
        mail_history = InviteOrgs.objects.filter(monitoring=self.object)
        is_mail_history_exist = mail_history.exists()

        self.queryform = InviteOrgsQueryForm(self.request.GET)
        if self.queryform.is_valid():
            mail_history = self.queryform.apply(mail_history)

        context['mail_history'] = mail_history
        context['is_mail_history_exist'] = is_mail_history_exist

        return context


class RepresentativesView(LoginRequiredMixin, DetailView):
    template_name = "representatives.html"
    pk_url_kwarg = 'monitoring_pk'
    model = Monitoring

    def get_object(self, queryset=None):
        self.monitoring = super(RepresentativesView, self).get_object(queryset)
        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return self.monitoring

    def get_context_data(self, **kwargs):
        context = super(RepresentativesView, self).get_context_data(**kwargs)

        orgs = self.monitoring.organization_set.exclude(userprofile=None).order_by('name').prefetch_related('userprofile_set')

        queryform = RepresentativesQueryForm(self.request.GET)
        org_choices = [('', _('Organization is not selected'))] + list(orgs.values_list('pk', 'name'))
        queryform.fields['organization'].choices = org_choices

        orgusers = UserProfile.objects.filter(organization__monitoring=self.monitoring)
        representatives_exist = orgusers.exists()

        if queryform.is_valid():
            orgusers = queryform.apply(orgusers)
            org_pk = queryform.cleaned_data['organization']
            if org_pk:
                orgs = [Organization.objects.get(pk=org_pk)]

        queried_users = set(orgusers.values_list('pk', flat=True))

        for org in orgs:
            org.users = []
            for user in sorted(org.userprofile_set.all(), key=lambda u: u.full_name):
                if user.pk in queried_users:
                    scores = Score.objects.filter(task__organization=org).values_list('pk', flat=True)
                    user.comments = user.user.comment_comments.filter(object_pk__in=scores)
                    org.users.append(user)

        context['orgs'] = [org for org in orgs if org.users]
        context['representatives_exist'] = representatives_exist
        context['queryform'] = queryform

        return context


@login_required
def representatives_export(request, monitoring_pk):
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        raise PermissionDenied

    orgs = monitoring.organization_set.order_by('name')

    for org in orgs:
        org.users = []
        for user in sorted(org.userprofile_set.all(),  key=lambda m: m.full_name):
            scores = Score.objects.filter(task__organization=org).values_list('pk', flat=True)
            user.comments = user.user.comment_comments.filter(object_pk__in=scores)
            org.users.append(user)

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

    for org in orgs:
        for user in org.users:
            row = [
                int(user.user.is_active),
                org.name,
                user.user.first_name,
                user.user.last_name,
                user.user.email,
                user.phone,
                user.position,
                user.comments.count(),
                user.user.date_joined.date().isoformat(),
            ]
            writer.writerow(row)

    license = LicenseTextFragments.objects.filter(pk='license')
    if license:
        writer.writerow([u'#%s' % license[0].csv_footer])

    return response
