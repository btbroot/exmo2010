# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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
import tempfile
import zipfile
from cStringIO import StringIO

from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count
from django.db import transaction
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden, HttpResponseRedirect, Http404
from django.http import HttpResponse
from django.template import RequestContext
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.create_update import delete_object
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.forms.models import modelformset_factory

from accounts.forms import SettingsInvCodeForm
from bread_crumbs.views import breadcrumbs
from exmo2010.forms import CORE_MEDIA, MonitoringCommentStatForm
from exmo2010.helpers import comment_report
from exmo2010.models import *
from core.utils import UnicodeReader, UnicodeWriter
from exmo2010.view.helpers import *
from monitorings.forms import MonitoringForm, MonitoringFilterForm
from parameters.forms import ParamCritScoreFilterForm, ParameterTypeForm


def set_npa_params(request, m_id):
    """
    Страница 'Выбрать согласованные параметры'.

    """
    # На админа проверять не надо. Они и так все is_expertA.
    if not request.user.is_active or not request.user.profile.is_expertA:
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk=m_id)
    parameters = monitoring.parameter_set.all()
    ParameterTypeFormSet = modelformset_factory(Parameter,
                                                extra=0,
                                                form=ParameterTypeForm)
    if request.method == "POST":
        formset = ParameterTypeFormSet(request.POST, queryset=parameters)
        # Нельзя изменять опубликованные мониторинги.
        if monitoring.status == Monitoring.MONITORING_PUBLISH:
            messages.warning(request, _("Forbidden to modify already "
                                        "published monitorings."), 'warning')
        else:
            if formset.is_valid():
                formset.save()
                messages.success(request, _("Changes have saved."))
    else:
        formset = ParameterTypeFormSet(queryset=parameters)

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs)

    if request.expert:
        current_title = _('Monitoring cycle')
    else:
        current_title = _('Rating') if monitoring.status == 5 else _('Tasks')

    return render_to_response('set_npa_params.html',
        {"formset": formset, "monitoring": monitoring, "current_title": current_title},
        context_instance=RequestContext(request))


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
                (_('status'), 'status', 'status', int, Monitoring.MONITORING_STATUS),
                )
    title = _('Monitoring list')

    #todo: remove this
    active_tasks = None
    if request.user.is_active and request.user.userprofile.is_organization:
        active_tasks = Task.objects.filter(
            organization__monitoring__status = Monitoring.MONITORING_INTERACT,
            organization__in = request.user.profile.organization.all(),
            status = Task.TASK_APPROVED,
        )
        invcodeform = SettingsInvCodeForm()
    else:
        invcodeform = None

    if not queryset.count() and not request.user.has_perm('exmo2010.create_monitoring', Monitoring()):
        return HttpResponseForbidden(_('Forbidden'))

    crumbs = ['Home']
    breadcrumbs(request, crumbs)
    current_title = _('Monitoring cycles')

    return table(
        request,
        headers,
        queryset = queryset,
        paginate_by = 25,
        extra_context = {
            'current_title': current_title,
            'title': title,
            'fakeobject': Monitoring(),
            'active_tasks': active_tasks,
            'invcodeform': invcodeform,
        },
    )


@login_required
def monitoring_manager(request, id, method):
    """
    Удаление/редактирование/пересчет мониторинга.

    """
    redirect = '%s?%s' % (reverse('exmo2010:monitoring_list'), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    monitoring = get_object_or_404(Monitoring, pk=id)
    if method == 'delete':
        if not request.user.has_perm('exmo2010.delete_monitoring', monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        title = _('Delete monitoring %s') % monitoring

        crumbs = ['Home', 'Monitoring']
        breadcrumbs(request, crumbs)
        current_title = _('Delete monitoring cycle')

        return delete_object(
            request,
            model = Monitoring,
            object_id = id,
            post_delete_redirect = redirect,
            extra_context = {
                'current_title': current_title,
                'title': title,
                'deleted_objects': Task.objects.filter(organization__monitoring = monitoring),
                }
            )
    else: #update
        if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        title = _('Edit monitoring %s') % monitoring
        if request.method == 'POST':
            form = MonitoringForm(request.POST, instance=monitoring)
            if form.is_valid():
                cd = form.cleaned_data
                m = form.save()
                questionnaire = m.get_questionnaire()
                # Удаление опроса.
                if cd.get("add_questionnaire") == False and questionnaire:
                    questionnaire.delete()
                elif cd.get("add_questionnaire") == True and not questionnaire:
                    questionnaire = Questionnaire(monitoring=m)
                    questionnaire.save()
                return HttpResponseRedirect(redirect)
        else:
            form = MonitoringForm(instance=monitoring,
                initial={"add_questionnaire": monitoring.has_questionnaire()})

        crumbs = ['Home', 'Monitoring']
        breadcrumbs(request, crumbs)
        current_title = _('Edit monitoring cycle')

        return render_to_response(
            'monitoring_form.html',
            {
                'current_title': current_title,
                'title': title,
                'form': form,
                'media': form.media,
                'object': monitoring,
            },
            context_instance=RequestContext(request))


@login_required
def monitoring_add(request):
    """
    Создание мониторинга
    """
    if not request.user.has_perm('exmo2010.create_monitoring', Monitoring()):
        return HttpResponseForbidden(_('Forbidden'))
    title = _('Add new monitoring')
    if request.method == 'POST':
        form = MonitoringForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            with transaction.commit_on_success():
                # Чтобы нельзя было создать удачно мониторинг, а потом словить
                # ошибку создания опроса для него.
                monitoring_instance = form.save()
                if cd.get("add_questionnaire"):
                    questionnaire = Questionnaire(monitoring=monitoring_instance)
                    questionnaire.save()
            redirect = reverse('exmo2010:monitoring_manager',
                args=[monitoring_instance.pk, 'update'])
            return HttpResponseRedirect(redirect)
    else:
        form = MonitoringForm()
        form.fields['status'].choices = Monitoring.MONITORING_STATUS_NEW

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs)
    current_title = _('Add monitoring cycle')

    return render_to_response('monitoring_form.html',
            {'current_title': current_title, 'media': form.media, 'form': form, 'title': title,
             'formset': None,}, context_instance=RequestContext(request))


#update rating twice in a day
#@cache_page(60 * 60 * 12)
#todo: remove this
def monitoring_rating_color(request, id):
  monitoring = get_object_or_404(Monitoring, pk = id)
  if not request.user.has_perm('exmo2010.rating_monitoring', monitoring): return HttpResponseForbidden(_('Forbidden'))

  rating_list, avg = rating(monitoring)

  rating_list_with_categories = []
  num_categories = 4 #number for division
  rating_piece = rating_list[0]['openness'] // num_categories
  for rating_object in rating_list:
    div_result = rating_object['openness'] // rating_piece
    category = 4
    for i in range(1,num_categories):
        if div_result > num_categories - i:
            category = i
            break
    rating_object['category'] = category

    rating_list_with_categories.append(rating_object)

  return render_to_response('rating_color.html', {
        'monitoring': monitoring,
        'object_list': rating_list_with_categories,
        'average': avg,
    }, context_instance=RequestContext(request))


def monitoring_rating(request, m_id):
    """
    Вывод мониторинга.

    """
    monitoring = get_object_or_404(Monitoring, pk=m_id)
    if not request.user.has_perm('exmo2010.rating_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    title = _('Rating')

    has_npa = monitoring.has_npa
    rating_type, parameter_list, form = rating_type_parameter(request, monitoring, has_npa)
    rating_list, avg = rating(monitoring, parameters=parameter_list, rating_type=rating_type)

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs)

    if request.expert:
        current_title = _('Monitoring cycle')
    else:
        current_title = _('Rating') if monitoring.status == 5 else _('Tasks')

    total_orgs = total_orgs_translate(avg, rating_list, rating_type)

    return render_to_response('rating.html', {
        'monitoring': monitoring,
        'has_npa': has_npa,
        'object_list': rating_list,
        'rating_type': rating_type,
        'average': avg,
        'total_orgs': total_orgs,
        'current_title': current_title,
        'title': title,
        'form': form,
    }, context_instance=RequestContext(request))


@login_required
def monitoring_by_criteria_mass_export(request, id):
    """
    Экспорт по критерию
    Архив из CVS файлов -- по файлу на критерий.

    """
    monitoring = get_object_or_404(Monitoring, pk = id)
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
    response['Content-Disposition'] = 'attachment; filename=monitoring-%s.zip' % id
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
def monitoring_by_experts(request, id):
    """
    Статистика мониторинга по экспертам.

    """
    monitoring = get_object_or_404(Monitoring, pk=id)
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

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs)

    if request.expert:
        current_title = _('Monitoring cycle')
    else:
        current_title = _('Rating') if monitoring.status == 5 else _('Tasks')

    return table(
        request,
        headers,
        queryset=queryset,
        paginate_by=15,
        extra_context={
            'monitoring': monitoring,
            'current_title': current_title,
            'title': title,
        },
        template_name="expert_list.html",
    )


#todo: remove
@login_required
def monitoring_info(request, id):
    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    organization_all_count = Organization.objects.filter(monitoring = monitoring).distinct().count()
    organization_open_count = Organization.objects.filter(monitoring = monitoring, task__status = Task.TASK_OPEN).count()
    organization_ready_count = Organization.objects.filter(monitoring = monitoring, task__status = Task.TASK_READY).count()
    organization_approved_count = Organization.objects.filter(monitoring = monitoring, task__status = Task.TASK_APPROVED).count()
    organization_with_task_count = Organization.objects.filter(monitoring = monitoring, task__status__isnull = False).distinct().count()
    extra_context = {
            'organization_all_count': organization_all_count,
            'organization_open_count': organization_open_count,
            'organization_ready_count': organization_ready_count,
            'organization_approved_count': organization_approved_count,
            'organization_with_task_count': organization_with_task_count,
    }


@login_required
def monitoring_parameter_filter(request, m_id):
    """
    Отчёт по параметру и критерию
    """
    if not (request.user.profile.is_expert or request.user.is_superuser):
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk=m_id)
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
            t_check = cd.get("t_check")
            if t_check:
                t_st_list.append(Task.TASK_CHECKED)
            t_approved = cd.get("t_approved")
            if t_approved:
                t_st_list.append(Task.TASK_APPROVED)

            queryset = queryset.filter(task__status__in=t_st_list)

            if request.user.profile.is_expertB and not (request.user.has_perm('exmo2010.admin_monitoring',
                monitoring) or request.user.profile.is_expertA or monitoring.is_publish):
                queryset = queryset.filter(task__user=request.user)

    else:
        form = ParamCritScoreFilterForm(monitoring=monitoring)
        hide = 1

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs)

    if request.expert:
        current_title = _('Monitoring cycle')
    else:
        current_title = _('Rating') if monitoring.status == 5 else _('Tasks')

    return render_to_response('monitoring_parameter_filter.html', {
        'form': form,
        'object_list': queryset,
        'monitoring': monitoring,
        'current_title': current_title,
        'hide': hide
    }, context_instance=RequestContext(request))


@login_required
def monitoring_parameter_found_report(request, id):
    """
    Отчёт по наличию параметра.

    """
    monitoring = get_object_or_404(Monitoring, pk=id)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    title = _('Report for %s by parameter and found') % monitoring
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
    return render_to_response('monitoring_parameter_found_report.html', {
        'monitoring': monitoring,
        'title': title,
        'object_list': object_list,
        'score_count_total': score_count_total,
        'organization_count_total': organization_count_total,
        'score_per_organization_total': score_per_organization_total,
    }, context_instance=RequestContext(request))


@login_required
def monitoring_parameter_export(request, id):
    """
    Экспорт параметров в CSV
    """
    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    parameters = Parameter.objects.filter(monitoring = monitoring)
    response = HttpResponse(mimetype = 'application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=monitoring-parameters-%s.csv' % id
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
def monitoring_organization_export(request, id):
    """
    Экспорт организаций в CSV.

    """
    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    organizations = Organization.objects.filter(monitoring = monitoring)
    response = HttpResponse(mimetype = 'application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=monitoring-orgaization-%s.csv' % id
    response.encoding = 'UTF-16'
    writer = UnicodeWriter(response)
    writer.writerow([
        '#Name',
        'Url',
        'Comments',
        'Keywords',
    ])
    for o in organizations:
        out = (
            o.name,
            o.url,
            o.comments,
        )
        keywords = ", ".join([k.name for k in o.tags])
        out += (keywords,)
        writer.writerow(out)
    return response


@login_required
@csrf_protect
def monitoring_organization_import(request, id):
    """
    Импорт организаций из CSV.

    """
    from reversion import revision
    must_register = False
    if revision.is_registered(Organization):
        revision.unregister(Organization)
        must_register = True

    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    if not request.FILES.has_key('orgfile'):
        return HttpResponseRedirect(reverse('exmo2010:monitoring_list'))
    reader = UnicodeReader(request.FILES['orgfile'])
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
                errLog.append("row %d (csv). Empty organization name" % reader.line_num)
                continue
            if row[1]  == '':
                errLog.append("row %d (csv). Empty organization url" % reader.line_num)
                continue
            try:
                name = row[0]
                organization = Organization.objects.get(monitoring=monitoring,
                    name=name)
            except Organization.DoesNotExist:
                organization = Organization()
                organization.monitoring = monitoring
            except Exception, e:
                errLog.append("row %d. %s" % (reader.line_num, e))
                continue
            try:
                organization.name = name.strip()
                organization.url = row[1].strip()
                organization.comments = row[2]
                organization.keywords = row[3]
                organization.inv_code = generate_inv_code(6)
                organization.full_clean()
                organization.save()
            except ValidationError, e:
                errLog.append("row %d (validation). %s" % (
                    reader.line_num,
                    '; '.join(['%s: %s' % (i[0], ', '.join(i[1])) for i in e.message_dict.items()])))
            except Exception, e:
                errLog.append("row %d. %s" % (reader.line_num, e))
            else:
                rowOKCount += 1
    except csv.Error, e:
        errLog.append("row %d (csv). %s" % (reader.line_num, e))
    title = _('Import organization from CSV for monitoring %s') % monitoring

    if must_register:
        revision.register(Organization)

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs, monitoring)
    current_title = _('Import organization')

    return render_to_response('monitoring_import_log.html', {
      'monitoring': monitoring,
      'file': request.FILES['orgfile'],
      'errLog': errLog,
      'rowOKCount': rowOKCount,
      'rowALLCount': rowALLCount,
      'current_title': current_title,
      'title': title,
    }, context_instance=RequestContext(request))


@login_required
@csrf_protect
def monitoring_parameter_import(request, id):
    """
    Импорт параметров из CSV.

    """
    from reversion import revision
    must_register = False
    if revision.is_registered(Parameter):
        revision.unregister(Parameter)
        must_register = True

    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    if not request.FILES.has_key('paramfile'):
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
           errLog.append("row %d (csv). %s" % (reader.line_num, e))
    title = _('Import parameter from CSV for monitoring %s') % monitoring

    if must_register:
        revision.register(Parameter)

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs, monitoring)
    current_title = _('Import parameter')

    return render_to_response('monitoring_import_log.html', {
      'monitoring': monitoring,
      'file': request.FILES['paramfile'],
      'errLog': errLog,
      'rowOKCount': rowOKCount,
      'rowALLCount': rowALLCount,
      'current_title': current_title,
      'title': title,
    }, context_instance=RequestContext(request))


@login_required
@csrf_protect
def monitoring_comment_report(request, id):
    monitoring = get_object_or_404(Monitoring, pk=id)
    time_to_answer = monitoring.time_to_answer
    if not (request.user.profile.is_expertA or request.user.is_superuser):
        return HttpResponseForbidden(_('Forbidden'))
    title = _('Comment report for %s') % monitoring

    form = MonitoringCommentStatForm(
        monitoring=monitoring,
        initial={'time_to_answer': time_to_answer})

    start_date = monitoring.interact_date
    if not start_date:

        crumbs = ['Home', 'Monitoring']
        breadcrumbs(request, crumbs)

        return render_to_response(
            "msg.html", {
                'msg': _('Start date for interact not defined.')
            }, context_instance=RequestContext(request))

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

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs)

    if request.expert:
        current_title = _('Monitoring cycle')
    else:
        current_title = _('Rating') if monitoring.status == 5 else _('Tasks')

    return render_to_response('monitoring_comment_report.html', {
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
        'current_title': current_title,
        'title': title,
        'media': CORE_MEDIA,
        }, context_instance=RequestContext(request))


def monitoring_report(request, report_type='inprogress', monitoring_id=None):
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
            status=Monitoring.MONITORING_PUBLISH
        ).exclude(
            hidden=True
        ).order_by('-rate_date')
    elif report_type == 'finished':
        all_monitorings = Monitoring.objects.exclude(
            hidden=True
        ).filter(
            status=Monitoring.MONITORING_PUBLISH
        ).order_by('-publish_date')
    if monitoring_id:
        monitorings = Monitoring.objects.filter(
            status=Monitoring.MONITORING_PUBLISH,
            pk=monitoring_id,
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

    crumbs = ['Home']
    breadcrumbs(request, crumbs)
    current_title = _('Statistics')

    return render_to_response('monitoring_report.html',
                              {
                                  'paginator': paginator_list,
                                  'monitorings': monitorings,
                                  'report_type': report_type,
                                  'current_title': current_title,
                                  'title': title,
                                  'monitoring_id': monitoring_id,
                                  'all_monitorings': all_monitorings,
                              },
                              RequestContext(request),
                              )


def ratings(request):
    """
    Рейтинги.

    """
    m_id = request.GET.get('monitoring')
    mform = MonitoringFilterForm(request.GET)
    title = _('Ratings')
    current_title = _('Ratings')

    context = {
        'title': title,
        'current_title': current_title,
        'report': True,
        'mform': mform,
    }

    if m_id:
        monitoring = get_object_or_404(Monitoring, pk=m_id)
        if not request.user.has_perm('exmo2010.rating_monitoring', monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        has_npa = monitoring.has_npa
        rating_type, parameter_list, form = rating_type_parameter(request, monitoring, has_npa)
        rating_list, avg = rating(monitoring, parameters=parameter_list, rating_type=rating_type)
        con = {
            'monitoring': monitoring,
            'has_npa': has_npa,
            'object_list': rating_list,
            'rating_type': rating_type,
            'average': avg,
            'form': form,
        }
        context.update(con)
        context['total_orgs'] = total_orgs_translate(avg, rating_list, rating_type)

    crumbs = ['Home']
    breadcrumbs(request, crumbs)

    return render_to_response('rating_report.html', context, context_instance=RequestContext(request))
