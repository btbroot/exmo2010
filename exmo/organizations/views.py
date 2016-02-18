# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2016 IRSI LTD
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
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.forms.models import modelform_factory
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DeleteView, DetailView, UpdateView
from django.utils.translation import ugettext as _

from .forms import OrganizationsQueryForm, RepresentativesQueryForm
from core.views import LoginRequiredMixin
from core.widgets import ModelMultiRawInput
from exmo2010.models import (
    Monitoring, Organization, Score, UserProfile, OrgUser)
from modeltranslation_utils import CurLocaleModelForm


class GroupActionForm(forms.Form):
    orgs = forms.ModelMultipleChoiceField(queryset=Organization.objects.all(), widget=ModelMultiRawInput)
    action = forms.ChoiceField(choices=[('hide_recommendations', ''), ('unhide_recommendations', '')])


class ManageOrgsView(LoginRequiredMixin, DetailView):
    template_name = "manage_monitoring/organizations.html"
    pk_url_kwarg = 'monitoring_pk'
    model = Monitoring

    def get_object(self, queryset=None):
        self.monitoring = super(ManageOrgsView, self).get_object(queryset)
        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return self.monitoring

    def get_context_data(self, **kwargs):
        context = super(ManageOrgsView, self).get_context_data(**kwargs)

        organizations = Organization.objects.filter(monitoring=self.object).annotate(tasks_count=Count('task'))
        context['orgs_exist'] = organizations.exists()

        queryform = OrganizationsQueryForm(self.request.GET)
        if queryform.is_valid():
            organizations = queryform.apply(organizations)

        context['organizations'] = organizations
        context['queryform'] = queryform

        form = GroupActionForm()
        form.fields['orgs'].queryset = self.monitoring.organization_set.all()
        context['group_action_form'] = form

        return context

    def post(self, request, *args, **kwargs):
        monitoring = self.get_object()

        form = GroupActionForm(request.POST)
        form.fields['orgs'].queryset = monitoring.organization_set.all()
        if form.is_valid():
            action = form.cleaned_data['action']
            orgs = Organization.objects.filter(pk__in=[x.pk for x in form.cleaned_data['orgs']])
            if action == 'hide_recommendations':
                orgs.update(recommendations_hidden=True)
                msg = _("Recommendations of given orgs will be hidden.")
            if action == 'unhide_recommendations':
                orgs.update(recommendations_hidden=False)
                msg = _("Recommendations of given orgs will be visible.")

            messages.success(self.request, msg)
            return redirect('exmo2010:manage_orgs', monitoring.pk)
        else:
            messages.error(self.request, _("Form invalid."))
            return redirect('exmo2010:manage_orgs', monitoring.pk)


class OrganizationMixin(LoginRequiredMixin):
    context_object_name = 'org'

    def get_context_data(self, **kwargs):
        context = super(OrganizationMixin, self).get_context_data(**kwargs)
        context['monitoring'] = self.monitoring
        return context

    def get_success_url(self):
        url = reverse('exmo2010:manage_orgs', args=[self.object.monitoring.pk])
        return '%s?%s' % (url, self.request.GET.urlencode())


class OrganizationEditView(OrganizationMixin, UpdateView):
    template_name = "manage_monitoring/organization_edit.html"

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


class OrganizationDeleteView(OrganizationMixin, DeleteView):
    template_name = "manage_monitoring/organization_delete.html"

    def get_object(self, queryset=None):
        org = get_object_or_404(Organization, pk=self.kwargs['org_pk'])
        self.monitoring = org.monitoring

        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return org


class RepresentativesView(LoginRequiredMixin, DetailView):
    template_name = "manage_monitoring/representatives.html"
    pk_url_kwarg = 'monitoring_pk'
    model = Monitoring

    def get_object(self, queryset=None):
        self.monitoring = super(RepresentativesView, self).get_object(queryset)
        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return self.monitoring

    def get_context_data(self, **kwargs):
        context = super(RepresentativesView, self).get_context_data(**kwargs)

        queryform = RepresentativesQueryForm(self.monitoring, self.request.GET)

        orgusers = UserProfile.objects.filter(organization__monitoring=self.monitoring)
        representatives_exist = orgusers.exists()

        orgs = self.monitoring.organization_set.exclude(userprofile=None).order_by('name').prefetch_related('userprofile_set')

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
                    user.seen = OrgUser.objects.filter(userprofile=user, organization=org, seen=True).exists()
                    org.users.append(user)

        context['orgs'] = [org for org in orgs if org.users]
        context['representatives_exist'] = representatives_exist
        context['queryform'] = queryform

        return context
