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
import copy
import csv
import os
import re
import tempfile
import zipfile
from cStringIO import StringIO
from collections import defaultdict, OrderedDict

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib import messages
from django.db.models import Count, Q
from django.db import transaction
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden, HttpResponseRedirect, Http404
from django.http import HttpResponse
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.generic.edit import ProcessFormView, ModelFormMixin
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext
from django.utils import simplejson
from django.forms.models import modelformset_factory

from accounts.forms import SettingsInvCodeForm
from core.helpers import table
from core.utils import UnicodeReader, UnicodeWriter
from custom_comments.forms import MonitoringCommentStatForm
from custom_comments.utils import comment_report
from exmo2010.forms import CORE_MEDIA
from exmo2010.models import *
from monitorings.forms import MonitoringForm, TableSettingsForm
from parameters.forms import ParamCritScoreFilterForm, ParameterDynForm, ParameterTypeForm


@login_required
def set_npa_params(request, monitoring_pk):
    """
    Страница 'Выбрать согласованные параметры'.

    """
    # На админа проверять не надо. Они и так все is_expertA.
    if not request.user.is_active or not request.user.profile.is_expertA:
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    parameters = monitoring.parameter_set.all()
    ParameterTypeFormSet = modelformset_factory(Parameter,
                                                extra=0,
                                                form=ParameterTypeForm)
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

    context = {"formset": formset, "monitoring": monitoring,}
    return TemplateResponse(request, 'set_npa_params.html', context)


def _get_monitoring_list(request):
    monitorings_pk = []
    for m in Monitoring.objects.all().select_related():
        if request.user.has_perm('exmo2010.view_monitoring', m):
            monitorings_pk.append(m.pk)
    queryset = Monitoring.objects.filter(
        pk__in=monitorings_pk).order_by('-publish_date')
    return queryset


def monitoring_list(request):
    """
    Список мониторингов.

    """
    queryset = _get_monitoring_list(request)

    headers =   (
                (_('monitoring'), 'name', 'name', None, None),
                (_('status'), 'status', 'status', int, MONITORING_STATUS),
                )
    title = _('Monitoring list')

    #todo: remove this
    active_tasks = None
    if request.user.is_active and request.user.userprofile.is_organization:
        active_tasks = Task.objects.filter(
            organization__monitoring__status=MONITORING_INTERACTION,
            organization__in=request.user.profile.organization.all(),
            status=Task.TASK_APPROVED,
        )
        invcodeform = SettingsInvCodeForm()
    else:
        invcodeform = None

    if not queryset.count() and not request.user.has_perm('exmo2010.create_monitoring', Monitoring()):
        return HttpResponseForbidden(_('Forbidden'))

    return table(
        request,
        headers,
        queryset = queryset,
        paginate_by = 25,
        extra_context = {
            'title': title,
            'fakeobject': Monitoring(),
            'active_tasks': active_tasks,
            'invcodeform': invcodeform,
        },
    )


class MonitoringManagerView(SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):
    """
    Generic view to edit or delete monitoring
    """

    model = Monitoring
    context_object_name = "object"
    form_class = MonitoringForm
    template_name = "monitoring_form.html"
    extra_context = {}
    pk_url_kwarg = 'monitoring_pk'

    def get_redirect(self, request):
        redirect = '%s?%s' % (reverse('exmo2010:monitoring_list'), request.GET.urlencode())
        redirect = redirect.replace("%", "%%")
        return redirect

    def get_context_data(self, **kwargs):
        context = super(MonitoringManagerView, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

    def get(self, request, *args, **kwargs):
        self.success_url = self.get_redirect(request)
        self.object = self.get_object()
        if self.kwargs["method"] == 'delete':
            if not request.user.has_perm('exmo2010.delete_monitoring', self.object):
                return HttpResponseForbidden(_('Forbidden'))

            title = _('Delete monitoring %s') % self.object
            self.template_name = "exmo2010/monitoring_confirm_delete.html"
            self.extra_context = {
                'title': title,
                'deleted_objects': Task.objects.filter(organization__monitoring=self.object),
            }

        if self.kwargs["method"] == 'update':
            if not request.user.has_perm('exmo2010.edit_monitoring', self.object):
                return HttpResponseForbidden(_('Forbidden'))
            title = _('Edit monitoring %s') % self.object
            self.extra_context = {
                'title': title,
            }

        return super(MonitoringManagerView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.success_url = self.get_redirect(request)
        self.object = self.get_object()
        if self.kwargs["method"] == 'delete':
            self.object = self.get_object()
            self.object.delete()
            return HttpResponseRedirect(self.get_success_url())
        elif self.kwargs["method"] == 'update':
            return super(MonitoringManagerView, self).post(request, *args, **kwargs)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(MonitoringManagerView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        cd = form.cleaned_data
        m = form.save()
        questionnaire = m.get_questionnaire()
        if cd.get("add_questionnaire") and questionnaire:
            questionnaire.delete()
        elif cd.get("add_questionnaire") and not questionnaire:
            questionnaire = Questionnaire(monitoring=m)
            questionnaire.save()
        return super(MonitoringManagerView, self).form_valid(form)


@login_required
def monitoring_add(request):
    """
    Create monitoring.

    """
    if not request.user.has_perm('exmo2010.create_monitoring', Monitoring()):
        return HttpResponseForbidden(_('Forbidden'))
    if request.method == 'POST':
        form = MonitoringForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            with transaction.commit_on_success():
                # Чтобы нельзя было создать удачно мониторинг, а потом словить
                # ошибку создания опроса для него.
                monitoring = form.save()
                if cd.get("add_questionnaire"):
                    questionnaire = Questionnaire(monitoring=monitoring)
                    questionnaire.save()
            redirect = reverse('exmo2010:monitoring_update', kwargs={'monitoring_pk': monitoring.pk})
            return HttpResponseRedirect(redirect)
    else:
        form = MonitoringForm()
        form.fields['status'].choices = Monitoring.MONITORING_STATUS_NEW

    context = {
        'media': form.media,
        'form': form,
        'title': _('Add new monitoring'),
        'formset': None
    }
    return TemplateResponse(request, 'monitoring_form.html', context)


def monitoring_rating(request, monitoring_pk):
    """Return a response containing the rating table,
    the table settings form, and the parameter selection form.
    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.rating_monitoring', monitoring) \
            or not request.user.is_anonymous() and request.user.profile.is_expertB \
            and not request.user.is_superuser and monitoring.status != 5:
        return HttpResponseForbidden(_('Forbidden'))

    has_npa = monitoring.has_npa
    rating_type, parameter_list, form = _rating_type_parameter(request, monitoring, has_npa)
    rating_list, avg = rating(monitoring, parameters=parameter_list, rating_type=rating_type)

    total_orgs = _total_orgs_translate(avg, rating_list, rating_type)

    name_filter = request.GET.get('name_filter', '')

    if name_filter:
        tasks = set(Task.objects.order_by().filter(organization__name__icontains=name_filter).values_list('pk', flat=True))
        rating_list = [t for t in rating_list if t.pk in tasks]

    if request.user.is_active:
        profile = request.user.profile
        representatives = request.GET.get('representatives', None)
        comment_quantity = request.GET.get('comment_quantity', None)
        initial_openness = request.GET.get('initial_openness', None)
        final_openness = request.GET.get('final_openness', None)
        difference = request.GET.get('difference', None)

        if representatives is not None or comment_quantity is not None or initial_openness is not None or final_openness is not None or difference is not None:
            table_settings = TableSettingsForm(request.GET)
            if table_settings.is_valid():
                data = table_settings.cleaned_data
                profile.rt_representatives = data['representatives']
                profile.rt_comment_quantity = data['comment_quantity']
                profile.rt_initial_openness = data['initial_openness']
                profile.rt_final_openness = data['final_openness']
                profile.rt_difference = data['difference']
                profile.save()
        else:
            table_settings = TableSettingsForm(initial={'representatives': profile.rt_representatives,
                                                    'comment_quantity': profile.rt_comment_quantity,
                                                    'initial_openness': profile.rt_initial_openness,
                                                    'final_openness': profile.rt_final_openness,
                                                    'difference': profile.rt_difference, })
    else:
        table_settings = TableSettingsForm()

    return TemplateResponse(request, 'rating.html', {
        'monitoring': monitoring,
        'has_npa': has_npa,
        'object_list': rating_list,
        'rating_type': rating_type,
        'average': avg,
        'total_orgs': total_orgs,
        'title': monitoring.name,
        'form': form,
        'table_form': table_settings,
        'name_filter': name_filter,
        'show_initial_openness': monitoring.status in Monitoring.after_interaction_status,
    })


@login_required
def monitoring_by_criteria_mass_export(request, monitoring_pk):
    """
    Экспорт по критерию
    Архив из CVS файлов -- по файлу на критерий.

    """
    monitoring = get_object_or_404(Monitoring, pk = monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
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
        row = copy.deepcopy(row_template)
        if header_row:
            for criteria in row.keys():
                row[criteria] = [''] + [ p.code for p in parameters ]
                writer[criteria].writerow(row[criteria])
            header_row = False
            row = copy.deepcopy(row_template)
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
        return HttpResponseForbidden(_('Forbidden'))
    experts = Task.objects.filter(organization__monitoring = monitoring).values('user').annotate(cuser=Count('user'))
    title = _('Experts of monitoring %s') % monitoring.name
    epk = [e['user'] for e in experts]
    org_list = "( %s )" % " ,".join([str(o.pk) for o in Organization.objects.filter(monitoring = monitoring)])
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
        extra_context={
            'monitoring': monitoring,
            'title': title,
        },
        template_name="expert_list.html",
    )


@login_required
def monitoring_parameter_filter(request, monitoring_pk):
    """
    Отчёт по параметру и критерию
    """
    if not (request.user.profile.is_expert or request.user.is_superuser):
        return HttpResponseForbidden(_('Forbidden'))
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

    return TemplateResponse(request, 'monitoring_parameter_filter.html', {
        'form': form,
        'object_list': queryset,
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
        return HttpResponseForbidden(_('Forbidden'))
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
    object_list=[]
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

    title = _('Parameter found report of %(monitoring)s') % {'monitoring': monitoring}

    return TemplateResponse(request, 'monitoring_parameter_found_report.html', {
        'monitoring': monitoring,
        'title': title,
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
    monitoring = get_object_or_404(Monitoring, pk = monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    parameters = Parameter.objects.filter(monitoring = monitoring)
    response = HttpResponse(mimetype = 'application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=monitoring-parameters-%s.csv' % monitoring_pk
    response.encoding = 'UTF-16'
    writer = UnicodeWriter(response)
    writer.writerow([
        '#Code',
        'Name',
        'Description',
        'Complete',
        'Topical',
        'Accessible',
        'Hypertext',
        'Document',
        'Image',
        'Weight',
        'Keywords',
    ])
    for p in parameters:
        out = (
            p.code,
            p.name,
            p.description,
            int(p.complete),
            int(p.topical),
            int(p.accessible),
            int(p.hypertext),
            int(p.document),
            int(p.image),
            p.weight
        )
        keywords = ", ".join([k.name for k in p.tags])
        out += (keywords,)
        writer.writerow(out)
    return response


@login_required
def monitoring_organization_export(request, monitoring_pk):
    """
    Экспорт организаций в CSV.

    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
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
        'Comments',
        'Keywords',
    ])
    for o in organizations:
        out = (
            o.name,
            o.url,
            o.email,
            o.phone,
            o.comments,
        )
        keywords = ", ".join([k.name for k in o.tags])
        out += (keywords,)
        writer.writerow(out)
    return response


@login_required
@csrf_protect
def monitoring_organization_import(request, monitoring_pk):
    """
    Импорт организаций из CSV.

    """
    from reversion import revision
    must_register = False
    if revision.is_registered(Organization):
        revision.unregister(Organization)
        must_register = True

    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    if not 'orgfile' in request.FILES:
        return HttpResponseRedirect(reverse('exmo2010:monitoring_list'))
    reader = UnicodeReader(request.FILES['orgfile'])
    errLog = []
    indexes = {}
    rowOKCount = 0
    rowALLCount = 0

    try:
        for row in reader:
            if rowALLCount == 0 and row[0] and row[0].startswith('#'):
                for key in ['name', 'url', 'email', 'phone', 'comments', 'keywords']:
                    for item in row:
                        if item and key in item.lower():
                            indexes[key] = row.index(item)
                continue

            if not 'name' in indexes:
                errLog.append("header row (csv). Field 'Name' does not exist")
                break

            rowALLCount += 1

            if row[0] and row[0].startswith('#'):
                errLog.append("row %d. Starts with '#'. Skipped" % rowALLCount)
                continue
            if row[indexes['name']] == '':
                errLog.append("row %d (csv). Empty organization name" % rowALLCount)
                continue
            try:
                organization = Organization.objects.get(monitoring=monitoring, name=row[indexes['name']])
            except Organization.DoesNotExist:
                organization = Organization()
                organization.monitoring = monitoring
            except Exception, e:
                errLog.append("row %d. %s" % (rowALLCount, e))
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
                errLog.append("row %d (validation). %s" % (
                    rowALLCount,
                    '; '.join(['%s: %s' % (i[0], ', '.join(i[1])) for i in e.message_dict.items()])))
            except Exception, e:
                errLog.append("row %d. %s" % (rowALLCount, e))
            else:
                rowOKCount += 1
    except csv.Error, e:
        errLog.append(_("row %(row)d (csv). %(raw)s") % {'row': reader.line_num, 'raw': e})
    except UnicodeError:
        errLog.append(_("File, you are loading is not valid CSV."))
    except Exception, e:
        errLog.append(_("Import error: %s." % e))
    title = _('Import organization from CSV for monitoring %s') % monitoring

    if must_register:
        revision.register(Organization)

    return TemplateResponse(request, 'monitoring_import_log.html', {
        'monitoring': monitoring,
        'file': request.FILES['orgfile'],
        'errLog': errLog,
        'rowOKCount': rowOKCount,
        'rowALLCount': rowALLCount,
        'title': title,
    })


@login_required
@csrf_protect
def monitoring_parameter_import(request, monitoring_pk):
    """
    Импорт параметров из CSV.

    """
    from reversion import revision
    must_register = False
    if revision.is_registered(Parameter):
        revision.unregister(Parameter)
        must_register = True

    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    if not 'paramfile' in request.FILES:
        return HttpResponseRedirect(reverse('exmo2010:monitoring_list'))
    reader = UnicodeReader(request.FILES['paramfile'])
    errLog = []
    rowOKCount = 0
    rowALLCount = 0
    try:
        for row in reader:
            rowALLCount += 1
            if row[0].startswith('#'):
                errLog.append("row %d. Starts with '#'. Skipped" % reader.line_num)
                continue
            if row[0] == '':
                errLog.append("row %d (csv). Empty code" % reader.line_num)
                continue
            if row[1] == '':
                errLog.append("row %d (csv). Empty name" % reader.line_num)
                continue
            try:
                code = row[0]
                name = row[1]
                parameter = Parameter.objects.get(monitoring=monitoring,
                    code=code, name=name)
            except Parameter.DoesNotExist:
                parameter = Parameter()
            except Exception, e:
                errLog.append("row %d. %s" % (reader.line_num, e))
                continue
            try:
                parameter.monitoring = monitoring
                parameter.code = code
                parameter.name = name
                # Присваиваем пустую строку, а не None.
                parameter.description = row[2] or ''
                parameter.complete = bool(int(row[3]))
                parameter.topical = bool(int(row[4]))
                parameter.accessible = bool(int(row[5]))
                parameter.hypertext = bool(int(row[6]))
                parameter.document = bool(int(row[7]))
                parameter.image = bool(int(row[8]))
                parameter.weight = row[9]
                parameter.keywords = row[10]
                parameter.full_clean()
                parameter.save()
            except ValidationError, e:
                errLog.append("row %d (validation). %s" % (
                    reader.line_num,
                    '; '.join(['%s: %s' % (i[0], ', '.join(i[1])) for i in e.message_dict.items()])))
            except Exception, e:
                errLog.append("row %d. %s" % (reader.line_num, e))
            else:
                rowOKCount += 1
    except csv.Error, e:
           errLog.append(_("row %(row)d (csv). %(raw)s") % {'row': reader.line_num, 'raw': e})
    except UnicodeError:
        errLog.append(_("File, you are loading is not valid CSV."))
    except Exception, e:
        errLog.append(_("Import error: %s." % e))
    title = _('Import parameter from CSV for monitoring %s') % monitoring

    if must_register:
        revision.register(Parameter)

    return TemplateResponse(request, 'monitoring_import_log.html', {
      'monitoring': monitoring,
      'file': request.FILES['paramfile'],
      'errLog': errLog,
      'rowOKCount': rowOKCount,
      'rowALLCount': rowALLCount,
      'title': title,
    })


@login_required
@csrf_protect
def monitoring_comment_report(request, monitoring_pk):
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    time_to_answer = monitoring.time_to_answer
    if not (request.user.profile.is_expertA or request.user.is_superuser):
        return HttpResponseForbidden(_('Forbidden'))
    title = _('Comment report for %s') % monitoring

    form = MonitoringCommentStatForm(
        monitoring=monitoring,
        initial={'time_to_answer': time_to_answer})

    start_date = monitoring.interact_date
    if not start_date:
        return TemplateResponse(request, "msg.html", {
                'msg': _('Start date for interact not defined.')
            })

    if request.method == "GET" and request.GET.__contains__('time_to_answer'):
        form = MonitoringCommentStatForm(request.GET, monitoring=monitoring)
        if form.is_valid():
            time_to_answer = int(form.cleaned_data['time_to_answer'])
            if time_to_answer != monitoring.time_to_answer:
                monitoring.time_to_answer = time_to_answer
                monitoring.save()

    report = comment_report(monitoring)

    comments_without_reply = report.get('comments_without_reply')
    fail_comments_without_reply = report.get('fail_comments_without_reply')
    fail_soon_comments_without_reply = report.get('fail_soon_comments_without_reply')
    fail_comments_with_reply = report.get('fail_comments_with_reply')
    comments_with_reply = report.get('comments_with_reply')
    org_comments = report.get('org_comments')
    org_all_comments = report.get('org_all_comments')
    iifd_all_comments = report.get('iifd_all_comments')
    active_organization_stats = report.get('active_organization_stats')
    total_org = report.get('total_org')
    reg_org = report.get('reg_org')
    active_iifd_person_stats = report.get('active_iifd_person_stats')

    return TemplateResponse(request, 'monitoring_comment_report.html', {
        'form': form,
        'comments_without_reply': comments_without_reply,
        'fail_comments_without_reply': fail_comments_without_reply,
        'fail_soon_comments_without_reply': fail_soon_comments_without_reply,
        'fail_comments_with_reply': fail_comments_with_reply,
        'comments_with_reply': comments_with_reply,
        'org_comments': org_comments,
        'org_all_comments': org_all_comments,
        'iifd_comments': iifd_all_comments,
        'active_organization_stats': active_organization_stats,
        'total_org': total_org.count(),
        'reg_org': reg_org.count(),
        'active_iifd_person_stats': active_iifd_person_stats,
        'time_to_answer': time_to_answer,
        'monitoring': monitoring,
        'title': title,
        'media': CORE_MEDIA,
        })


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
    """Returns table of monitorings' rating data,
    optionally filters table by monitoring
    """

    title = _('Ratings')

    name_filter = request.GET.get('name_filter', '')
    if name_filter:
        monitoring_list = Monitoring.objects.filter(status=MONITORING_PUBLISHED,
                                                    name__icontains=name_filter).order_by('-publish_date')
    else:
        monitoring_list = Monitoring.objects.filter(status=MONITORING_PUBLISHED).order_by('-publish_date')

    user = request.user

    if not user.is_authenticated() or (user.is_active and not user.profile.is_organization
                                       and not user.profile.is_expert):
        monitoring_list = monitoring_list.filter(hidden=False)
    elif user.is_active and user.profile.is_organization and not user.profile.is_expert:
        monitoring_list = monitoring_list.filter(Q(hidden=False) | Q(organization__userprofile__user=user, hidden=True))
    elif user.is_active and user.profile.is_expertB and not user.profile.is_expertA:
        monitoring_list = monitoring_list.filter(Q(hidden=False) | Q(organization__task__user=user, hidden=True))

    monitoring_list = monitoring_list.annotate(org_count=Count('organization'))

    for m in monitoring_list:
        openness = m.openness_expression
        sql_openness = openness.get_sql_openness()
        sql_openness_initial = openness.get_sql_openness(initial=True)

        tasks = Task.approved_tasks.filter(organization__monitoring=m)
        tasks = tasks.extra(select={'task_openness': sql_openness,
                                    'task_openness_initial': sql_openness_initial},
                            order_by=['-task_openness'])
        openness_list = [t.task_openness for t in tasks if t.task_openness is not None]
        avg = reduce(lambda x, y: x + y, openness_list) / len(openness_list) if openness_list else None
        m.average = round(avg, 3) if avg else None

    context = {
        'title': title,
        'monitoring_list': monitoring_list,
        'name_filter': name_filter,
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


def _total_orgs_translate(avg, rating_list, rating_type):
    """
    Returns string containing organization count.

    Accepts arguments:
    avg - dictionary of average values of monitoring rating
    rating_list - list of rating data for monitoring
    rating_type - string/unicode type of monitoring, may be 'user' for example
    """
    text = ungettext(
        'Altogether, there is %(count)d organization in the monitoring cycle',
        'Altogether, there are %(count)d organizations in the monitoring cycle',
        avg['total_tasks']
    ) % {'count': avg['total_tasks']}

    if rating_type == 'user':
        text_for_users = ungettext(
            ', %(count)d of them has at least 1 relevant setting from users sample',
            ', %(count)d of them have at least 1 relevant setting from users sample',
            len(rating_list)
        ) % {'count': len(rating_list)}
        text += text_for_users
    text += '.'
    return text


def _rating_type_parameter(request, monitoring, has_npa=False):
    """
    Функция подготовки списка параметров и формы выбора параметров.

    """
    data = {}
    parameter_list = []

    rating_type_list = ('all', 'user')
    if has_npa:
        rating_type_list += ('npa', 'other')
    rating_type = request.GET.get('type', 'all')
    if rating_type not in rating_type_list:
        raise Http404

    parameters = Parameter.objects.filter(monitoring=monitoring)

    if rating_type == 'npa':
        parameter_list = parameters.filter(npa=True)
    elif rating_type == 'other':
        parameter_list = parameters.filter(npa=False)
    elif rating_type == 'user':
        data = request.GET
        query_string = request.META.get('QUERY_STRING')
        if query_string:
            parameter_ids = re.findall(r'\d+', query_string)
            parameter_list = parameters.filter(pk__in=parameter_ids)

    form = ParameterDynForm(data=data, monitoring=monitoring)

    return rating_type, parameter_list, form


def rating(monitoring, parameters=None, rating_type=None):
    """
    Create monitoring rating with or without parameters.
    Rerturns sorted tasks queryset and average openness dictionary.

    """
    tasks = Task.approved_tasks.filter(organization__monitoring=monitoring)\
                               .filter(score__pk__isnull=False)\
                               .order_by().distinct()

    avg = {
        'openness': None,
        'openness_initial': None,
        'openness_delta': None,
        'total_tasks': 0,
    }

    if parameters and rating_type == 'user':
        params_list = Parameter.objects.filter(pk__in=parameters)
        non_relevant = set(params_list[0].exclude.all())
        for item in params_list[1:]:
            non_relevant &= set(item.exclude.all())

        tasks = tasks.exclude(organization__in=list(non_relevant))

    if tasks.exists():
        openness = monitoring.openness_expression
        sql_openness = openness.get_sql_openness(parameters)
        sql_openness_initial = openness.get_sql_openness(parameters, initial=True)

        tasks = tasks.select_related('organization').extra(
            select={'task_openness': sql_openness, 'task_openness_initial': sql_openness_initial},
            where=['%s IS NOT NULL' % sql_openness],
            order_by=['-task_openness'])

        if tasks:
            max_rating = tasks[0].task_openness
            total_tasks = len(tasks)

            avg['total_tasks'] = total_tasks
            avg['openness'] = sum([t.task_openness for t in tasks]) / total_tasks
            avg['openness_initial'] = sum([t.task_openness_initial for t in tasks]) / total_tasks
            avg['openness_delta'] = round(avg['openness'] - avg['openness_initial'], 3)

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

            place = 1
            for task in tasks:
                users = orgusers_by_task[task.pk]
                comments = orgcomments_by_task[task.pk]

                task.comments = len(comments)
                task.repr_len = len(users)
                task.active_repr_len = len(set(comments))
                openness_delta_float = float(task.task_openness) - float(task.task_openness_initial)
                task.openness_delta = round(openness_delta_float, 3)

                if task.task_openness < max_rating:
                    place += 1
                    max_rating = task.task_openness

                task.place = place

            avg['repr_len'] = sum([t.repr_len for t in tasks]) / total_tasks
            avg['active_repr_len'] = sum([t.active_repr_len for t in tasks]) / total_tasks
            avg['comments'] = sum([t.comments for t in tasks]) / total_tasks

    return tasks, avg


class MonitoringExport(object):
    #отсортированные критерии для экспорта в csv
    CSV_CRITERIONS = [
        'name',
        'id',
        'found',
    ]
    CSV_CRITERIONS.extend(Parameter.OPTIONAL_CRITERIONS)
    CSV_CRITERIONS.extend(['social', 'type', 'revision'])

    def __init__(self, monitoring):
        self.monitoring = monitoring
        scores = list(Score.objects.raw(monitoring.sql_scores()))
        position = 0
        #dict with organization as keys and el as list of scores for json export
        self.tasks = OrderedDict()
        if not len(scores):
            return
        current_openness = None
        for score in scores:
            # skip score from non-approved task
            if score.task_status != Task.TASK_APPROVED:
                continue
            if not current_openness or score.task_openness != current_openness:
                position += 1
                current_openness = score.task_openness

            score_dict = {
                'name': score.parameter_name.strip(),
                'social': score.weight,
                'found': score.found,
                'type': 'npa' if score.parameter_npa else 'other',
                'revision': Score.REVISION_EXPORT[score.revision],
                'id': score.parameter_id,
            }
            if settings.DEBUG:
                score_dict['pk'] = score.pk
            for criteria in Parameter.OPTIONAL_CRITERIONS:
                row_criteria = getattr(score, criteria, -1)
                #for sql_v1: document and image always None
                if row_criteria is None:
                    row_criteria = -1
                row_criteria = float(row_criteria)
                if row_criteria > -1:
                    score_dict[criteria] = row_criteria

            if score.organization_id in self.tasks.keys():
                self.tasks[score.organization_id]['scores'].append(score_dict)
            else:
                if score.task_openness is not None:
                    score.task_openness = '%.3f' % score.task_openness
                if score.openness_initial is not None:
                    score.openness_initial = '%.3f' % score.openness_initial

                self.tasks[score.organization_id] = {
                    'scores': [score_dict, ],
                    'position': position,
                    'openness': score.task_openness,
                    'openness_initial': score.openness_initial,
                    'name': score.organization_name,
                    'id': score.organization_id,
                    'url': score.url,
                }

    def json(self):
        ret = {
            'monitoring': {
                'name': self.monitoring.name,
                'tasks': self.tasks.values(),
            }
        }
        json_dump_args = {}
        if settings.DEBUG:
            json_dump_args = {'indent': 2}
        response = HttpResponse(mimetype='application/json')
        response.encoding = 'UTF-8'
        response['Content-Disposition'] = \
            'attachment; filename=monitoring-%s.json' % self.monitoring.pk
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
        #csv HEAD
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
            "Revision"
        ])
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
                row.extend(
                    [
                        unicode(score_dict.get(c, "not relevant"))
                        for c in self.CSV_CRITERIONS
                    ])
                writer.writerow(row)
        return response


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

    export_format = request.GET.get('format', 'json')
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.rating_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    export = MonitoringExport(monitoring)
    r = HttpResponseForbidden(_('Forbidden'))
    if export_format == 'csv':
        r = export.csv()
    elif export_format == 'json':
        r = export.json()
    return r
