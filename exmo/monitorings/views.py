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
import csv
import os
import tempfile
import zipfile
from collections import defaultdict, OrderedDict
from copy import deepcopy
from cStringIO import StringIO
from operator import attrgetter

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.db import transaction, connection
from django.db.models import Count, Q
from django.db.utils import DEFAULT_DB_ALIAS
from django.forms import Form, ModelMultipleChoiceField, CheckboxSelectMultiple, BooleanField
from django.forms.models import modelformset_factory, modelform_factory
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic import DeleteView, DetailView, UpdateView
from reversion.revisions import default_revision_manager as revision

from .forms import MonitoringCopyForm, MonitoringsQueryForm, RatingsQueryForm, RatingQueryForm, ObserversGroupQueryForm
from auth.helpers import perm_filter
from core.helpers import table
from core.utils import UnicodeReader, UnicodeWriter, dictfetchall
from core.views import login_required_on_deny, LoginRequiredMixin
from custom_comments.utils import comment_report
from exmo2010.columns_picker import monitorings_index_columns_form, rating_columns_form
from exmo2010.forms import FilteredSelectMultiple
from exmo2010.models import (Claim, Clarification, LicenseTextFragments, Monitoring, ObserversGroup, Organization,
                             Parameter, Questionnaire, Score, Task, UserProfile, generate_inv_code)
from exmo2010.models.monitoring import MONITORING_PREPARE, MONITORING_PUBLISHED, MONITORING_STATUS, PUB
from modeltranslation_utils import CurLocaleModelForm
from parameters.forms import ParamCritScoreFilterForm, ParameterTypeForm
from perm_utils import annotate_exmo_perms


def avg(attr, items):
    """
    Calculate average attribute value for list of items, given attribute name.
    Values of None will be excluded from calculations. If resulting list is empty,
    average will be None
    """
    values = [val for val in map(attrgetter(attr), items) if val is not None]
    return round(sum(values) / len(values), 3) if values else None


@login_required
def set_npa_params(request, monitoring_pk):
    """
    Страница 'Выбрать согласованные параметры'.

    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        raise PermissionDenied

    parameters = monitoring.parameter_set.all()
    ParameterTypeFormSet = modelformset_factory(Parameter, extra=0, form=ParameterTypeForm)
    if request.method == "POST":
        formset = ParameterTypeFormSet(request.POST, queryset=parameters)
        # Нельзя изменять опубликованные мониторинги.
        if monitoring.status == MONITORING_PUBLISHED:
            messages.warning(request, _("Forbidden to modify already published monitorings."))
        else:
            if formset.is_valid():
                formset.save()
                messages.success(request, _("Changes have saved."))

    else:
        formset = ParameterTypeFormSet(queryset=parameters)

    context = {"formset": formset, "monitoring": monitoring}
    return TemplateResponse(request, 'manage_monitoring/set_npa_params.html', context)


@login_required
def monitorings_list(request, monitoring_status='unpublished'):
    """
    List of monitorings for experts
    """
    if not request.user.userprofile.is_expert:
        raise PermissionDenied

    # Process monitorings_index_columns_form data to know what columns to show in table
    columns_form = monitorings_index_columns_form(request)
    if columns_form.post_ok(request):
        # After form submission redirect to the same page.
        return HttpResponseRedirect(request.path)

    monitorings = perm_filter(request.user, 'view_monitoring', Monitoring.objects.all())

    template_name = 'home/monitorings_unpublished.html'
    queryform = MonitoringsQueryForm(request.GET)
    context = {'queryform': queryform, 'columns_form': columns_form}

    if monitoring_status == 'unpublished':
        monitorings = monitorings.exclude(status=MONITORING_PUBLISHED).order_by('-status', 'publish_date')
        db_statuses = monitorings.order_by('status').values_list('status', flat=True).distinct()

        if queryform.is_valid():
            monitorings = queryform.apply(monitorings)

        statuses = []
        for status, status_name in reversed(MONITORING_STATUS[:-1]):
            statuses.append({'name': status_name,
                             'unfiltered_monitorings_exist': status in db_statuses,
                             'monitorings_list': monitorings.filter(status=status)})

        context.update({'statuses': statuses})

    elif monitoring_status == 'published':
        template_name = 'home/monitorings_published.html'
        monitorings = monitorings.filter(status=MONITORING_PUBLISHED).order_by('-publish_date')
        monitorings_exist = monitorings.exists()

        if queryform.is_valid():
            monitorings = queryform.apply(monitorings)

        context.update({'monitorings': monitorings,
                        'monitorings_exist': monitorings_exist})

    return TemplateResponse(request, template_name, context)


class MonitoringMixin(LoginRequiredMixin):
    context_object_name = "monitoring"
    pk_url_kwarg = 'monitoring_pk'

    def get_success_url(self):
        return '%s?%s' % (reverse('exmo2010:monitorings_list'), self.request.GET.urlencode())


class MonitoringEditView(MonitoringMixin, UpdateView):
    """
    Generic view to edit or add monitoring
    """
    template_name = "monitoring_form.html"

    def get_initial(self):
        initial = super(MonitoringEditView, self).get_initial()
        if self.object:
            initial.update({'add_questionnaire': self.object.has_questionnaire})
        return initial

    def get_object(self, queryset=None):
        if 'monitoring_pk' in self.kwargs:
            # Existing monitoring edit page
            monitoring = get_object_or_404(Monitoring, pk=self.kwargs['monitoring_pk'])
            if not self.request.user.has_perm('exmo2010.admin_monitoring', monitoring):
                raise PermissionDenied
            return monitoring
        else:
            # New monitoring page
            if not self.request.user.has_perm('exmo2010.create_monitoring'):
                raise PermissionDenied
            return None

    def get_form_class(self):
        _modelform_kwargs = dict(model=Monitoring, form=CurLocaleModelForm, exclude=['time_to_answer'])
        if not self.object:
            # New monitoring form, status should be default (MONITORING_PREPARE)
            _modelform_kwargs['exclude'].append('status')

        form_class = modelform_factory(**_modelform_kwargs)

        # Add pseudo-field to toggle questionnaire addition in the form
        form_class.base_fields['add_questionnaire'] = BooleanField(required=False,
                                                                   label=_('Monitoring cycle with questionnaire'))

        return form_class

    def form_valid(self, form):
        with transaction.commit_on_success():
            monitoring = form.save()
            add_questionnaire = form.cleaned_data.get("add_questionnaire")
            has_questionnaire = monitoring.has_questionnaire()
            if not add_questionnaire and has_questionnaire:
                Questionnaire.objects.filter(monitoring=monitoring).delete()
            elif add_questionnaire and not has_questionnaire:
                Questionnaire.objects.create(monitoring=monitoring)
        return HttpResponseRedirect(self.get_success_url())


class MonitoringDeleteView(MonitoringMixin, DeleteView):
    template_name = "exmo2010/monitoring_confirm_delete.html"

    def get_object(self, queryset=None):
        monitoring = get_object_or_404(Monitoring, pk=self.kwargs['monitoring_pk'])
        if not self.request.user.has_perm('exmo2010.delete_monitoring', monitoring):
            raise PermissionDenied
        return monitoring

    def post(self, *args, **kwargs):
        monitoring = self.get_object()

        with transaction.commit_on_success():
            # To prevent memory exhaustion use _raw_delete() for scores and models below (BUG 2249)
            # TODO: after rewrite of comments code, delete score comments here, before scores deletion.
            Claim.objects.filter(score__parameter__monitoring=monitoring)._raw_delete(using=DEFAULT_DB_ALIAS)
            Clarification.objects.filter(score__parameter__monitoring=monitoring)._raw_delete(using=DEFAULT_DB_ALIAS)
            Score.objects.filter(parameter__monitoring=monitoring)._raw_delete(using=DEFAULT_DB_ALIAS)

            # Delete monitoring normally. This will still try to fetch scores, but they got deleted above and
            # should not consume all memory.
            monitoring.delete()
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(MonitoringDeleteView, self).get_context_data(**kwargs)
        tasks = Task.objects.filter(organization__monitoring=self.object)
        return dict(context, tasks=tasks.select_related('user__userprofile', 'organization'))


class MonitoringCopyView(LoginRequiredMixin, UpdateView):
    """
    Generic view to copy monitoring
    """
    context_object_name = "monitoring"
    pk_url_kwarg = "monitoring_pk"
    form_class = MonitoringCopyForm
    template_name = "monitoring_copy.html"

    def get_initial(self):
        initial = super(MonitoringCopyView, self).get_initial()
        initial.update({
            'status': MONITORING_PREPARE,
            'openness_expression': 8,
            'no_interact': False,
            'hidden': False,
            'add_questionnaire': False,
            'rate_date': None,
            'interact_date': None,
            'publish_date': None,
            'finishing_date': None,
        })
        return initial

    def get_object(self, queryset=None):
        self.monitoring = get_object_or_404(Monitoring, pk=self.kwargs['monitoring_pk'])
        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return self.monitoring

    def get_success_url(self):
        return '%s?%s' % (reverse('exmo2010:monitoring_update', args=[self.monitoring.pk]), self.request.GET.urlencode())

    def get_form_kwargs(self):
        kwargs = super(MonitoringCopyView, self).get_form_kwargs()
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({'instance': None})
        return kwargs

    def form_valid(self, form):
        with transaction.commit_on_success():
            origin_monitoring = self.get_object()
            self.monitoring = form.save()
            cd = form.cleaned_data

            if cd.get('add_questionnaire'):
                Questionnaire.objects.create(monitoring=self.monitoring)

            organization_map = {}
            task_map = {}
            parameter_map = {}

            orgs = Organization.objects.filter(monitoring=origin_monitoring)
            for org in orgs:
                copied_org = deepcopy(org)
                copied_org.id = None
                copied_org.monitoring = self.monitoring
                copied_org.inv_status = 'NTS'
                copied_org.inv_code = generate_inv_code(6)
                copied_org.save()
                organization_map[org.id] = copied_org.id

            if 'tasks' in cd.get('donors', []):
                for task in Task.objects.filter(organization__monitoring=origin_monitoring):
                    copied_task = deepcopy(task)
                    copied_task.id = None
                    copied_task.organization_id = organization_map[task.organization_id]
                    copied_task.save()
                    task_map[task.id] = copied_task.id

            if 'parameters' in cd.get('donors', []):
                for param in Parameter.objects.filter(monitoring=origin_monitoring):
                    copied_param = deepcopy(param)
                    copied_param.id = None
                    copied_param.monitoring = self.monitoring
                    copied_param.save()
                    copied_param.exclude.add(*[organization_map[x] for x in param.exclude.values_list('pk', flat=True)])
                    parameter_map[param.id] = copied_param.id

            scores = None
            if 'all_scores' in cd.get('donors', []):
                scores = Score.objects.filter(task__organization__monitoring=origin_monitoring,
                                              parameter__monitoring=origin_monitoring)
            elif 'current_scores' in cd.get('donors', []):
                scores = Score.objects.filter(task__organization__monitoring=origin_monitoring,
                                              parameter__monitoring=origin_monitoring,
                                              revision=Score.FINAL)
            if scores:
                bulk_of_scores = []
                for score in scores:
                    copied_score = deepcopy(score)
                    copied_score.id = None
                    copied_score.task_id = task_map[score.task_id]
                    copied_score.parameter_id = parameter_map[score.parameter_id]
                    bulk_of_scores.append(copied_score)

                # Disable 'auto_now' option to copy 'last_modified' field as is
                for field in Score._meta.local_fields:
                    if field.name == 'last_modified':
                        field.auto_now = False
                # Then create all scores in one query
                Score.objects.bulk_create(bulk_of_scores, batch_size=3000)
                # And restore 'auto_now' option
                for field in Score._meta.local_fields:
                    if field.name == 'last_modified':
                        field.auto_now = True

            if 'representatives' in cd.get('donors', []):
                users = UserProfile.objects.filter(user__groups__name='organizations',
                                                   organization__monitoring=origin_monitoring)
                for user in users:
                    orgs = [organization_map[org_pk] for org_pk in user.organization.values_list('pk', flat=True)
                            if org_pk in organization_map]
                    user.organization.add(*orgs)

        return HttpResponseRedirect(self.get_success_url())


@login_required_on_deny
def monitoring_rating(request, monitoring_pk):
    """
    Return a response containing the rating table,
    the table settings form, and the parameter selection form.
    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    user = request.user
    if not user.has_perm('exmo2010.view_monitoring', monitoring):
        raise PermissionDenied

    # Process rating_columns_form data to know what columns to show in table
    columns_form = rating_columns_form(request)
    if columns_form.post_ok(request):
        # After form submission redirect to the same page.
        return HttpResponseRedirect(request.path)

    # Process params_form - it will contain chosen params if rating_type is 'user'
    params_form = Form(request.GET)
    params_form.fields['params'] = ModelMultipleChoiceField(
        monitoring.parameter_set.all(), widget=CheckboxSelectMultiple)

    params = params_form.cleaned_data['params'] if params_form.is_valid() else None

    rating_type = request.GET.get('type', 'all')
    rating_list = monitoring.rating(params, rating_type)

    context = {
        'monitoring': monitoring,
        'rating_type': rating_type,
        'params_form': params_form,
        'rating_columns_form': columns_form,
    }

    orgs = set()
    if user.is_active and ObserversGroup.objects.filter(monitoring=monitoring, users=user).exists():
        orgs = orgs.union(set(user.observersgroup_set.filter(monitoring=monitoring).values_list('organizations__pk', flat=True)))

    if user.is_expert or monitoring.is_published:

        queryform = RatingQueryForm(request.GET)

        if queryform.is_valid():
            queryset = queryform.apply(monitoring.organization_set.all())
            orgs = orgs.union(set(queryset.values_list('pk', flat=True)))
            rating_list = [t for t in rating_list if t.organization.pk in orgs]

        approved_tasks = Task.approved_tasks.filter(organization__monitoring=monitoring).distinct()
        rating_stats = dict(_comments_stats(rating_list), **{
            'num_approved_tasks': approved_tasks.count(),
            'num_rated_tasks': len(rating_list),
            'openness': avg('task_openness', rating_list),
            'openness_initial': avg('task_openness_initial', rating_list),
            'openness_delta': avg('openness_delta', rating_list)
        })

        context.update({
            'rating_list': rating_list,
            'rating_stats': rating_stats,
            'queryform': queryform,
        })
    else:
        if user.is_organization:
            orgs = orgs.union(set(user.profile.organization.values_list('pk', flat=True)))
        rating_list = [t for t in rating_list if t.organization.pk in orgs]
        context.update({
            'rating_list': rating_list,
            'rating_stats': None
        })

    return TemplateResponse(request, 'rating.html', context)


def _comments_stats(tasks):
    '''
    Calculate and annotate each task in the list with comment statistics
    Return summary comment statistics.
    '''
    ntasks = len(tasks)
    if ntasks == 0:
        return {k: 0 for k in 'repr_len active_repr_len num_comments'.split()}

    orgusers_by_task, orgcomments_by_task = defaultdict(list), defaultdict(list)

    orgusers = User.objects.filter(userprofile__organization__task__in=tasks)\
                           .values_list('pk', 'userprofile__organization__task')
    for uid, tid in orgusers:
        orgusers_by_task[tid].append(uid)

    orgcomments = Comment.objects.filter(user__in=[uid for uid, tid in orgusers])\
                                 .values_list('user_id', 'object_pk')

    scores = Score.objects.filter(pk__in=[sid for uid, sid in orgcomments])
    tasks_by_scores = dict(scores.values_list('pk', 'task_id'))
    for uid, sid in orgcomments:
        if int(sid) in tasks_by_scores:
            orgcomments_by_task[tasks_by_scores[int(sid)]].append(uid)

    for task in tasks:
        task.num_comments = len(orgcomments_by_task[task.pk])
        task.repr_len = len(orgusers_by_task[task.pk])
        task.active_repr_len = len(set(orgcomments_by_task[task.pk]))

    return {
        'repr_len': sum(t.repr_len for t in tasks) / ntasks,
        'active_repr_len': sum(t.active_repr_len for t in tasks) / ntasks,
        'num_comments': sum(t.num_comments for t in tasks) / ntasks}


@login_required
def monitoring_by_criteria_mass_export(request, monitoring_pk):
    """
    Экспорт по критерию
    Архив из CVS файлов -- по файлу на критерий.

    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        raise PermissionDenied

    row_template = {
        'Found':      [],
        'Complete':   [],
        'Topical':    [],
        'Accessible': [],
        'Hypertext':  [],
        'Document':   [],
        'Image':      []
    }
    spool = {}
    writer = {}
    handle = {}
    for criteria in row_template.keys():
        spool[criteria] = tempfile.mkstemp()
        handle[criteria] = os.fdopen(spool[criteria][0], 'w')
        writer[criteria] = UnicodeWriter(handle[criteria])
    header_row = True
    parameters = Parameter.objects.filter(monitoring = monitoring)
    for task in Task.approved_tasks.filter(organization__monitoring = monitoring):
        row = deepcopy(row_template)
        if header_row:
            for criteria in row.keys():
                row[criteria] = [''] + [ p.code for p in parameters ]
                writer[criteria].writerow(row[criteria])
            header_row = False
            row = deepcopy(row_template)
        for criteria in row.keys():
            row[criteria] = [task.organization.name]
        for parameter in parameters:
            try:
                score = Score.objects.filter(task=task, parameter=parameter, revision=Score.REVISION_DEFAULT)[0]
                if task.organization in parameter.exclude.all():
                    raise IndexError
            except IndexError:
                row['Found'].append('')
                row['Complete'].append('')
                row['Topical'].append('')
                row['Accessible'].append('')
                row['Hypertext'].append('')
                row['Document'].append('')
                row['Image'].append('')
            else:
                row['Found'].append(score.found)
                if score.parameter.complete:
                    row['Complete'].append(score.complete)
                else:
                    row['Complete'].append('')
                if score.parameter.topical:
                    row['Topical'].append(score.topical)
                else:
                    row['Topical'].append('')
                if score.parameter.accessible:
                    row['Accessible'].append(score.accessible)
                else:
                    row['Accessible'].append('')
                if score.parameter.hypertext:
                    row['Hypertext'].append(score.hypertext)
                else:
                    row['Hypertext'].append('')
                if score.parameter.document:
                    row['Document'].append(score.document)
                else:
                    row['Document'].append('')
                if score.parameter.image:
                    row['Image'].append(score.image)
                else:
                    row['Image'].append('')
        for criteria in row.keys():
            writer[criteria].writerow(row[criteria])

    for criteria in row_template.keys():
        license = LicenseTextFragments.objects.filter(pk='license')
        if license:
            writer[criteria].writerow([u'#%s' % license[0].csv_footer])

    response = HttpResponse(mimetype = 'application/zip')
    response['Content-Disposition'] = 'attachment; filename=monitoring-%s.zip' % monitoring_pk
    buffer = StringIO()
    writer = zipfile.ZipFile(buffer, 'w')
    for criteria in row_template.keys():
        handle[criteria].close()
        writer.write(spool[criteria][1], criteria + '.csv')
        os.unlink(spool[criteria][1])
    writer.close()
    buffer.flush()
    response.write(buffer.getvalue())
    buffer.close()
    return response


@login_required
def monitoring_by_experts(request, monitoring_pk):
    """
    Статистика мониторинга по экспертам.

    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        raise PermissionDenied

    experts = Task.objects.filter(organization__monitoring=monitoring).values('user').annotate(cuser=Count('user'))
    epk = [e['user'] for e in experts]
    org_list = "( %s )" % " ,".join([str(o.pk) for o in Organization.objects.filter(monitoring=monitoring)])
    queryset = User.objects.filter(pk__in = epk).extra(select = {
        'open_tasks': 'select count(*) from %(task_table)s where %(task_table)s.user_id = %(user_table)s.id and status = %(status)s and %(task_table)s.organization_id in %(org_list)s' % {
            'task_table': Task._meta.db_table,
            'user_table': User._meta.db_table,
            'org_list': org_list,
            'status': Task.TASK_OPEN
            },
        'ready_tasks': 'select count(*) from %(task_table)s where %(task_table)s.user_id = %(user_table)s.id and status = %(status)s and %(task_table)s.organization_id in %(org_list)s' % {
            'task_table': Task._meta.db_table,
            'user_table': User._meta.db_table,
            'org_list': org_list,
            'status': Task.TASK_READY
            },
        'approved_tasks': 'select count(*) from %(task_table)s where %(task_table)s.user_id = %(user_table)s.id and status = %(status)s and %(task_table)s.organization_id in %(org_list)s' % {
            'task_table': Task._meta.db_table,
            'user_table': User._meta.db_table,
            'org_list': org_list,
            'status': Task.TASK_APPROVED
            },
        'all_tasks': 'select count(*) from %(task_table)s where %(task_table)s.user_id = %(user_table)s.id and %(task_table)s.organization_id in %(org_list)s' % {
            'task_table': Task._meta.db_table,
            'user_table': User._meta.db_table,
            'org_list': org_list,
            },
        })
    headers = (
          (_('Expert'), 'username', 'username', None, None),
          (_('Open tasks'), 'open_tasks', None, None, None),
          (_('Ready tasks'), 'ready_tasks', None, None, None),
          (_('Approved tasks'), 'approved_tasks', None, None, None),
          (_('All tasks'), 'all_tasks', None, None, None),
    )

    return table(
        request,
        headers,
        queryset=queryset,
        paginate_by=15,
        extra_context={'monitoring': annotate_exmo_perms(monitoring, request.user)},
        template_name="manage_monitoring/expert_list.html",
    )


@login_required
def monitoring_parameter_filter(request, monitoring_pk):
    """
    Отчёт по параметру и критерию
    """
    if not request.user.profile.is_expert:
        raise PermissionDenied

    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    queryset = None
    if request.method == "POST":
        hide = 0
        form = ParamCritScoreFilterForm(request.POST, monitoring=monitoring)
        if form.is_valid():
            cd = form.cleaned_data
            parameter = cd.get("parameter")
            queryset = Score.objects.filter(
                task__organization__monitoring=monitoring,
                parameter=parameter,
                revision=Score.REVISION_DEFAULT
            ).exclude(
                task__organization__in = parameter.exclude.all(),
            )

            # Оценки по критериям.
            found = cd.get("found")
            if found is not None:
                found_int = int(found)
                if found_int != 5:
                    queryset = queryset.filter(found=found_int)
            complete = cd.get("complete")
            if complete is not None:
                complete_int = int(complete)
                if complete_int != 5:
                    queryset = queryset.filter(complete=complete_int)
            topical = cd.get("topical")
            if topical is not None:
                topical_int = int(topical)
                if topical_int != 5:
                    queryset = queryset.filter(topical=topical_int)
            accessible = cd.get("accessible")
            if accessible is not None:
                accessible_int = int(accessible)
                if accessible_int != 5:
                    queryset = queryset.filter(accessible=accessible_int)
            hypertext = cd.get("hypertext")
            if hypertext is not None:
                hypertext_int = int(hypertext)
                if hypertext_int != 5:
                    queryset = queryset.filter(hypertext=hypertext_int)
            document = cd.get("document")
            if document is not None:
                document_int = int(document)
                if document_int != 5:
                    queryset = queryset.filter(document=document_int)
            image = cd.get("image")
            if image is not None:
                image_int = int(image)
                if image_int != 5:
                    queryset = queryset.filter(image=image_int)

            # Статусы задачи.
            t_st_list = []
            t_opened = cd.get("t_opened")
            if t_opened:
                t_st_list.append(Task.TASK_OPEN)
            t_closed = cd.get("t_closed")
            if t_closed:
                t_st_list.append(Task.TASK_CLOSED)
            t_approved = cd.get("t_approved")
            if t_approved:
                t_st_list.append(Task.TASK_APPROVED)

            queryset = queryset.filter(task__status__in=t_st_list)

            if request.user.profile.is_expertB and not (request.user.has_perm('exmo2010.admin_monitoring',
                monitoring) or request.user.profile.is_expertA or monitoring.is_published):
                queryset = queryset.filter(task__user=request.user)

    else:
        form = ParamCritScoreFilterForm(monitoring=monitoring)
        hide = 1

    return TemplateResponse(request, 'manage_monitoring/parameter_filter.html', {
        'form': form,
        'scores': queryset,
        'monitoring': monitoring,
        'hide': hide
    })


@login_required
def monitoring_parameter_found_report(request, monitoring_pk):
    """
    Отчёт по наличию параметра.

    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        raise PermissionDenied

    queryset = Parameter.objects.filter(monitoring = monitoring).extra(select={
            'organization_count':'''(select count(*) from %(organization_table)s where %(organization_table)s.monitoring_id = %(monitoring)s) -
                                    (select count(*) from %(parameterexclude_table)s where %(parameterexclude_table)s.parameter_id = %(parameter_table)s.id
                                        and %(parameterexclude_table)s.organization_id in
                                                (select id from %(organization_table)s where %(organization_table)s.monitoring_id = %(monitoring)s))''' % {
                'organization_table': Organization._meta.db_table,
                'monitoring': monitoring.pk,
                'parameterexclude_table': ('%s_%s') % ( Parameter._meta.db_table, 'exclude'),
                'parameter_table': Parameter._meta.db_table,
                }
        }
    )
    object_list = []
    score_count_total = 0
    organization_count_total = 0
    score_per_organization_total = 0
    queryset_list = list(queryset)
    for parameter in queryset_list:
        score_count = Score.objects.filter(
            task__organization__monitoring = monitoring,
            task__status = Task.TASK_APPROVED,
            found = 1,
            parameter = parameter,
            revision = Score.REVISION_DEFAULT,
        ).exclude(
            task__organization__in = parameter.exclude.all(),
        ).count()
        score_count_total += score_count
        organization_count_total += parameter.organization_count
        score_per_organization = 0
        if parameter.organization_count:
            score_per_organization = float(score_count) / parameter.organization_count * 100
        obj = {
            'parameter': parameter,
            'organization_count': parameter.organization_count,
            'score_count': score_count,
            'score_per_organization': score_per_organization,
        }
        object_list.append(obj)
    if organization_count_total:
        score_per_organization_total = float(score_count_total) / organization_count_total * 100

    return TemplateResponse(request, 'manage_monitoring/parameter_found_report.html', {
        'monitoring': monitoring,
        'object_list': object_list,
        'score_count_total': score_count_total,
        'organization_count_total': organization_count_total,
        'score_per_organization_total': score_per_organization_total,
    })


@login_required
def monitoring_parameter_export(request, monitoring_pk):
    """
    Экспорт параметров в CSV
    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        raise PermissionDenied

    parameters = Parameter.objects.filter(monitoring=monitoring)
    response = HttpResponse(mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=monitoring-parameters-%s.csv' % monitoring_pk
    response.encoding = 'UTF-16'
    writer = UnicodeWriter(response)
    writer.writerow([
        '#Code',
        'Name',
        'Grounds',
        'Rating procedure',
        'Notes',
        'Complete',
        'Topical',
        'Accessible',
        'Hypertext',
        'Document',
        'Image',
        'Weight',
    ])
    for p in parameters:
        out = (
            p.code,
            p.name,
            p.grounds,
            p.rating_procedure,
            p.notes,
            int(p.complete),
            int(p.topical),
            int(p.accessible),
            int(p.hypertext),
            int(p.document),
            int(p.image),
            p.weight
        )
        writer.writerow(out)
    license = LicenseTextFragments.objects.filter(pk='license')
    if license:
        writer.writerow([u'#%s' % license[0].csv_footer])

    return response


@login_required
def monitoring_organization_export(request, monitoring_pk):
    """
    Экспорт организаций в CSV.

    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        raise PermissionDenied

    organizations = Organization.objects.filter(monitoring=monitoring)
    response = HttpResponse(mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=monitoring-organization-%s.csv' % monitoring_pk
    response.encoding = 'UTF-16'
    writer = UnicodeWriter(response)
    writer.writerow([
        '#Name',
        'Url',
        'Email',
        'Phone',
        'Code',
        'Invitation link',
    ])
    for o in organizations:
        out = (
            o.name,
            o.url,
            o.email,
            o.phone,
            o.inv_code,
            request.build_absolute_uri(reverse('exmo2010:auth_orguser') + '?code={}'.format(o.inv_code)),
        )
        writer.writerow(out)
    license = LicenseTextFragments.objects.filter(pk='license')
    if license:
        writer.writerow([u'#%s' % license[0].csv_footer])

    return response


@login_required
@csrf_protect
def monitoring_organization_import(request, monitoring_pk):
    """
    Импорт организаций из CSV.

    """
    must_register = False
    if revision.is_registered(Organization):
        revision.unregister(Organization)
        must_register = True

    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        raise PermissionDenied
    if not 'orgfile' in request.FILES:
        return HttpResponseRedirect(reverse('exmo2010:monitorings_list'))
    reader = UnicodeReader(request.FILES['orgfile'])
    errors = []
    indexes = {}
    rowOKCount = 0
    row_num = 0
    try:
        for row_num, row in enumerate(reader, start=1):
            if row[0] and row[0].startswith('#'):
                for key in ['name', 'url', 'email', 'phone']:
                    for item in row:
                        if item and key in item.lower():
                            indexes[key] = row.index(item)
                errors.append("row %d. Starts with '#'. Skipped" % row_num)
                continue

            if not 'name' in indexes:
                errors.append("header row (csv). Field 'Name' does not exist")
                break

            if row[indexes['name']] == '':
                errors.append("row %d (csv). Empty organization name" % row_num)
                continue
            try:
                organization = Organization.objects.get(monitoring=monitoring, name=row[indexes['name']])
            except Organization.DoesNotExist:
                organization = Organization()
                organization.monitoring = monitoring
            except Exception, e:
                errors.append("row %d. %s" % (row_num, e))
                continue
            try:
                for key in indexes.keys():
                    cell = row[indexes[key]]
                    if key in ['email', 'phone'] and cell:
                        cell = replace_string(cell)
                    setattr(organization, key, cell.strip() if cell else '')
                organization.inv_code = generate_inv_code(6)
                organization.full_clean()
                organization.save()
            except ValidationError, e:
                errors.append("row %d (validation). %s" % (
                    row_num,
                    '; '.join(['%s: %s' % (i[0], ', '.join(i[1])) for i in e.message_dict.items()])))
            except Exception, e:
                errors.append("row %d. %s" % (row_num, e))
            else:
                rowOKCount += 1
    except csv.Error, e:
        errors.append(_("row %(row)d (csv). %(raw)s") % {'row': row_num, 'raw': e})
    except UnicodeError:
        errors.append(_("File, you are loading is not valid CSV."))
    except Exception, e:
        errors.append(_("Import error: %s." % e))

    if must_register:
        revision.register(Organization)

    return TemplateResponse(request, 'exmo2010/csv_import_log.html', {
        'monitoring': monitoring,
        'errors': errors,
        'row_count': '{}/{}'.format(rowOKCount, row_num),
    })


@login_required
@csrf_protect
def monitoring_parameter_import(request, monitoring_pk):
    """
    Импорт параметров из CSV.

    """
    must_register = False
    if revision.is_registered(Parameter):
        revision.unregister(Parameter)
        must_register = True

    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        raise PermissionDenied
    if not 'paramfile' in request.FILES:
        return HttpResponseRedirect(reverse('exmo2010:monitorings_list'))
    reader = UnicodeReader(request.FILES['paramfile'])
    errors = []
    rowOKCount = 0
    row_num = 0
    try:
        for row_num, row in enumerate(reader, start=1):
            if row[0].startswith('#'):
                errors.append("row %d. Starts with '#'. Skipped" % row_num)
                continue
            if row[0] == '':
                errors.append("row %d (csv). Empty code" % row_num)
                continue
            if row[1] == '':
                errors.append("row %d (csv). Empty name" % row_num)
                continue
            try:
                code = row[0]
                name = row[1]
                parameter = Parameter.objects.get(monitoring=monitoring, code=code, name=name)
            except Parameter.DoesNotExist:
                parameter = Parameter()
            except Exception, e:
                errors.append("row %d. %s" % (row_num, e))
                continue
            try:
                parameter.monitoring = monitoring
                parameter.code = code
                parameter.name = name
                # Присваиваем пустую строку, а не None.
                parameter.grounds = row[2] or ''
                parameter.rating_procedure = row[3] or ''
                parameter.notes = row[4] or ''
                parameter.complete = bool(int(row[5]))
                parameter.topical = bool(int(row[6]))
                parameter.accessible = bool(int(row[7]))
                parameter.hypertext = bool(int(row[8]))
                parameter.document = bool(int(row[9]))
                parameter.image = bool(int(row[10]))
                parameter.weight = row[11]
                parameter.full_clean()
                parameter.save()
            except ValidationError, e:
                errors.append("row %d (validation). %s" % (
                    row_num,
                    '; '.join(['%s: %s' % (i[0], ', '.join(i[1])) for i in e.message_dict.items()])))
            except Exception, e:
                errors.append("row %d. %s" % (row_num, e))
            else:
                rowOKCount += 1
    except csv.Error, e:
        errors.append(_("row %(row)d (csv). %(raw)s") % {'row': row_num, 'raw': e})
    except UnicodeError:
        errors.append(_("File, you are loading is not valid CSV."))
    except Exception, e:
        errors.append(_("Import error: %s." % e))

    if must_register:
        revision.register(Parameter)

    return TemplateResponse(request, 'exmo2010/csv_import_log.html', {
        'monitoring': monitoring,
        'errors': errors,
        'row_count': '{}/{}'.format(rowOKCount, row_num),
    })


class MonitoringCommentReportView(LoginRequiredMixin, UpdateView):
    template_name = 'manage_monitoring/comment_report.html'
    pk_url_kwarg = 'monitoring_pk'
    model = Monitoring

    def get_object(self, queryset=None):
        self.monitoring = super(MonitoringCommentReportView, self).get_object(queryset)
        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied

        return self.monitoring

    def get_form_class(self):
        return modelform_factory(Monitoring, fields=['time_to_answer'])

    def get_success_url(self):
        return reverse('exmo2010:monitoring_comment_report', args=[self.monitoring.pk])

    def get_context_data(self, **kwargs):
        context = super(MonitoringCommentReportView, self).get_context_data(**kwargs)
        context.update(comment_report(self.monitoring))
        return context


def monitoring_report(request, report_type='inprogress', monitoring_pk=None):
    """
    Статистика по мониторингам.

    """
    if report_type not in ['inprogress', 'finished']:
        raise Http404

    all_monitorings = None
    paginator_list = None
    title = _('Monitoring statistics')

    if report_type == 'inprogress':
        all_monitorings = Monitoring.objects.exclude(
            status=MONITORING_PUBLISHED
        ).exclude(
            hidden=True
        ).order_by('-rate_date')
    elif report_type == 'finished':
        all_monitorings = Monitoring.objects.exclude(
            hidden=True
        ).filter(
            status=MONITORING_PUBLISHED
        ).order_by('-publish_date')
    if monitoring_pk:
        monitorings = Monitoring.objects.filter(
            status=MONITORING_PUBLISHED,
            pk=monitoring_pk,
            hidden=False)
    else:
        monitorings = all_monitorings

        paginator = Paginator(monitorings, 10)
        try:
            page = int(request.GET.get('page', '1'))
            if page < 1:
                page = 1
        except ValueError:
            page = 1

        try:
            paginator_list = paginator.page(page)
        except (EmptyPage, InvalidPage):
            paginator_list = paginator.page(1)

        monitorings = paginator_list.object_list

    return TemplateResponse(request, 'monitoring_report.html', {
        'paginator': paginator_list,
        'monitorings': monitorings,
        'report_type': report_type,
        'title': title,
        'monitoring_id': monitoring_pk,
        'all_monitorings': all_monitorings,
    })


def ratings(request):
    """
    Returns table of monitorings rating data, optionally filters table by monitoring.

    """
    user = request.user
    queryset = Monitoring.objects.all()

    mon = Q(status=PUB, hidden=False)
    own = Q()
    can_observe = Q()
    appendix = Q()
    if user.is_active and ObserversGroup.objects.filter(users=user).exists():
        can_observe = Q(observersgroup__users=user)

    if user.is_expertA:
        mon = Q(status=PUB)
    elif user.is_expertB:
        mon = Q(hidden=False)
        appendix = Q(status=PUB)
        own = Q(organization__task__user=user)
    elif user.is_organization:
        own = Q(organization__userprofile__user=user)

    queryset = queryset.filter(mon | own | can_observe, appendix).distinct()

    queryset = queryset.annotate(org_count=Count('organization')).order_by('-publish_date')

    for m in queryset:
        if m.status == MONITORING_PUBLISHED:
            sql_openness = m.openness_expression.get_sql_openness()
            tasks = Task.approved_tasks.filter(organization__monitoring=m).extra(select={'_openness': sql_openness})
            m.avg_openness = avg('_openness', tasks)
        else:
            m.avg_openness = 0

    queryform = RatingsQueryForm(request.GET)

    if queryform.is_valid():
        queryset = queryform.apply(queryset)

    context = {
        'monitoring_list': queryset,
        'queryform': queryform,
    }

    return TemplateResponse(request, 'ratings.html', context)


def replace_string(cell):
    cell = cell.replace(';', ',')
    cell = cell.replace(', ', ',')
    cell = cell.replace(',\n', ',')
    cell = cell.replace(',\t', ',')
    cell = cell.replace('\t', ',')
    tmp = []
    for item in cell.split(','):
        tmp.append(item.strip())
    cell = ', '.join(tmp)
    return cell


class MonitoringExport(object):
    def __init__(self, monitoring):
        self.monitoring = monitoring
        cursor = connection.cursor()
        cursor.execute(monitoring.sql_scores())
        scores = dictfetchall(cursor)
        cursor.close()

        if not len(scores):
            return

        if monitoring.openness_expression.code == 1:
            criteria = Parameter.OPTIONAL_CRITERIA_V1
        else:
            criteria = Parameter.OPTIONAL_CRITERIA

        # dict with organization as keys and el as list of scores for json export
        self.tasks = OrderedDict()
        rating_place = 0
        current_openness = None

        for score in scores:
            # skip score from non-approved task
            if score['task_status'] != Task.TASK_APPROVED:
                continue

            if not current_openness or score['task_openness'] != current_openness:
                rating_place += 1
                current_openness = score['task_openness']

            score_dict = {
                'name': score['parameter_name'].strip(),
                'social': score['weight'],
                'found': score['found'],
                'type': 'npa' if score['parameter_npa'] else 'other',
                'revision': Score.REVISION_EXPORT[score['revision']],
                'id': score['parameter_id'],
                'links': (score['links'] or '').strip(),
                'recommendations': (score['recommendations'] or '').strip(),
            }
            if settings.DEBUG:
                score_dict['pk'] = score['id']

            for criterion in criteria:
                if score[criterion] != -1:
                    score_dict[criterion] = float(score[criterion])

            if score['organization_id'] in self.tasks.keys():
                self.tasks[score['organization_id']]['scores'].append(score_dict)
            else:
                if score['task_openness'] is not None:
                    score['task_openness'] = '%.3f' % score['task_openness']
                if score['openness_initial'] is not None:
                    score['openness_initial'] = '%.3f' % score['openness_initial']

                self.tasks[score['organization_id']] = {
                    'scores': [score_dict, ],
                    'position': rating_place,
                    'openness': score['task_openness'],
                    'openness_initial': score['openness_initial'],
                    'name': score['organization_name'],
                    'id': score['organization_id'],
                    'url': score['url'],
                }

    def json(self):
        ret = {
            'monitoring': {
                'name': self.monitoring.name,
                'tasks': self.tasks.values(),
            },
        }
        license = LicenseTextFragments.objects.filter(pk='license')
        json_license = license[0].json_license if license else {}
        if json_license:
            ret.update({'license': json_license})
        json_dump_args = {}
        if settings.DEBUG:
            json_dump_args = {'indent': 2}
        response = HttpResponse(mimetype='application/json')
        response.encoding = 'UTF-8'
        response['Content-Disposition'] = 'attachment; filename=monitoring-%s.json' % self.monitoring.pk
        response.write(
            simplejson.dumps(
                ret, **json_dump_args
            ).decode("unicode_escape").encode("utf8"))
        return response

    def csv(self):
        response = HttpResponse(mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = \
            'attachment; filename=monitoring-%s.csv' % self.monitoring.pk
        response.encoding = 'UTF-16'
        writer = UnicodeWriter(response)
        # csv HEAD
        writer.writerow([
            "#Monitoring",
            "Organization",
            "Organization_id",
            "Position",
            "Initial Openness",
            "Openness",
            "Parameter",
            "Parameter_id",
            "Found",
            "Complete",
            "Topical",
            "Accessible",
            "Hypertext",
            "Document",
            "Image",
            "Social",
            "Type",
            "Revision",
            "Links",
            "Recommendations"
        ])

        score_fields = ['name', 'id', 'found'] + Parameter.OPTIONAL_CRITERIA
        score_fields += ['social', 'type', 'revision', 'links', 'recommendations']
        for task in self.tasks.values():
            for score_dict in task['scores']:
                row = [
                    self.monitoring.name,
                    task['name'],
                    task['id'],
                    task['position'],
                    task['openness_initial'],
                    task['openness'],
                ]
                row.extend([unicode(score_dict.get(c, "not relevant")) for c in score_fields])
                writer.writerow(row)
        # csv FOOTER
        license = LicenseTextFragments.objects.filter(pk='license')
        if license:
            writer.writerow([u'#%s' % license[0].csv_footer])

        return response


@login_required_on_deny
def monitoring_export(request, monitoring_pk):
    """
    :param request:
        django request object with GET var 'format'
        export format could be 'json' or 'csv'
    :param monitoring_pk:
        monitoring pk
    :return:
        json or csv with all scores for monitoring
    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.view_monitoring', monitoring):
        raise PermissionDenied

    export_format = request.GET.get('format', 'json')
    if export_format == 'csv':
        return MonitoringExport(monitoring).csv()
    elif export_format == 'json':
        return MonitoringExport(monitoring).json()
    raise PermissionDenied


class ObserversGroupView(LoginRequiredMixin, DetailView):
    template_name = "manage_monitoring/observers_groups.html"
    pk_url_kwarg = 'monitoring_pk'
    model = Monitoring

    def get_object(self, queryset=None):
        monitoring = super(ObserversGroupView, self).get_object(queryset)
        if not self.request.user.has_perm('exmo2010.admin_monitoring', monitoring):
            raise PermissionDenied
        return monitoring

    def get_context_data(self, **kwargs):
        context = super(ObserversGroupView, self).get_context_data(**kwargs)

        obs_groups = ObserversGroup.objects.filter(monitoring=self.object).order_by('name')
        context['is_obs_groups_exists'] = obs_groups.exists()

        queryform = ObserversGroupQueryForm(self.request.GET)

        if queryform.is_valid():
            obs_groups = queryform.apply(obs_groups)

        context['obs_groups'] = obs_groups
        context['queryform'] = queryform

        return context


class ObserversGroupMixin(LoginRequiredMixin):
    context_object_name = 'obs_group'

    def get_context_data(self, **kwargs):
        context = super(ObserversGroupMixin, self).get_context_data(**kwargs)
        return dict(context, monitoring=self.monitoring)

    def get_success_url(self):
        return reverse('exmo2010:observers_groups', args=[self.monitoring.pk])


class ObserversGroupEditView(ObserversGroupMixin, UpdateView):
    template_name = "manage_monitoring/observers_group_edit.html"

    def get_object(self, queryset=None):
        if 'obs_group_pk' in self.kwargs:
            # Existing observers group edit page
            obj = get_object_or_404(ObserversGroup, pk=self.kwargs['obs_group_pk'])
            self.monitoring = obj.monitoring
        else:
            # New observers group page
            obj = None
            self.monitoring = get_object_or_404(Monitoring, pk=self.kwargs['monitoring_pk'])

        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return obj

    def get_form_class(self):
        widgets = {
            'organizations': FilteredSelectMultiple('', is_stacked=False),
            'users': FilteredSelectMultiple('', is_stacked=False),
        }
        form_class = modelform_factory(model=ObserversGroup, widgets=widgets)
        form_class.base_fields['organizations'].queryset = Organization.objects.filter(monitoring=self.monitoring)
        users = User.objects.filter(is_active=True, is_superuser=False)\
                    .exclude(groups__name='expertsA')\
                    .select_related('userprofile')
        form_class.base_fields['users'].choices = [(u.id, u"%s — %s" % (u.profile.full_name, u.email)) for u in users]

        return form_class

    def get_initial(self):
        self.initial['monitoring'] = self.monitoring
        return super(ObserversGroupEditView, self).get_initial()


class ObserversGroupDeleteView(ObserversGroupMixin, DeleteView):
    template_name = "manage_monitoring/observers_group_confirm_delete.html"

    def get_object(self, queryset=None):
        obs_group = get_object_or_404(ObserversGroup, pk=self.kwargs['obs_group_pk'])
        self.monitoring = obs_group.monitoring

        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return obs_group
