# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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

"""
Модуль вью для работы с мониторингами
"""

import csv
import simplejson
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count
from django.db import transaction
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.http import HttpResponseForbidden, HttpResponseRedirect, Http404
from django.http import HttpResponse
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.create_update import  delete_object
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.forms.models import inlineformset_factory, modelformset_factory
from exmo2010.models import Organization, Parameter, Score, Task, Questionnaire
from exmo2010.models import Monitoring, QQuestion, AnswerVariant
from exmo2010.models import MonitoringStatus, QUESTION_TYPE_CHOICES
from exmo2010.models import generate_inv_code
from exmo2010.view.helpers import table
from exmo2010.view.helpers import rating, rating_type_parameter
from exmo2010.forms import MonitoringForm, MonitoringStatusForm, CORE_MEDIA
from exmo2010.forms import ParamCritScoreFilterForm, SettingsInvCodeForm
from exmo2010.utils import UnicodeReader, UnicodeWriter
from exmo2010.forms import MonitoringStatusBaseFormset, ParameterTypeForm


def set_npa_params(request, m_id):
    """Страница 'Выбрать согласованные параметры'."""
    # На админа проверять не надо. Они и так все is_expertA.
    if not request.user.profile.is_expertA:
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk=m_id)
    parameters = monitoring.parameter_set.all()
    ParameterTypeFormSet = modelformset_factory(Parameter, extra=0,
        form=ParameterTypeForm)
    if request.method == "POST":
        formset = ParameterTypeFormSet(request.POST, queryset=parameters)
        # Нельзя изменять опубликованные мониторинги.
        if monitoring.status == Monitoring.MONITORING_PUBLISH:
            messages.warning(request, _("Forbidden to modify already "
                                        "published monitorings."))
        else:
            if formset.is_valid():
                formset.save()
                messages.success(request, _("Changes have saved."))
    else:
        formset = ParameterTypeFormSet(queryset=parameters)
    return render_to_response('exmo2010/set_npa_params.html',
        {"formset": formset, "monitoring": monitoring},
        context_instance=RequestContext(request))



def _get_monitoring_list(request):
    monitorings_pk = []
    for m in Monitoring.objects.all().select_related():
        if request.user.has_perm('exmo2010.view_monitoring', m):
            monitorings_pk.append(m.pk)
    queryset = Monitoring.objects.filter(pk__in=monitorings_pk).extra(
        select={'start_date': Monitoring().prepare_date_sql_inline(
            Monitoring.MONITORING_PUBLISH),
                }
    ).order_by('-start_date')
    return queryset

def monitoring_list(request):
    """
    Список мониторингов
    """
    queryset = _get_monitoring_list(request)

    headers =   (
                (_('monitoring'), 'name', 'name', None, None),
                (_('status'), 'status', 'status', int, Monitoring.MONITORING_STATUS),
                )

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
    return table(
        request,
        headers,
        queryset = queryset,
        paginate_by = 25,
        extra_context = {
            #'title': _('Monitoring list'),
            'fakeobject': Monitoring(),
            'active_tasks': active_tasks,
            'invcodeform': invcodeform,
        },
    )



@login_required
def monitoring_manager(request, id, method):
    """
    Удаление/редактирование/пересчет мониторинга
    """
    redirect = '%s?%s' % (reverse('exmo2010:monitoring_list'), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    monitoring = get_object_or_404(Monitoring, pk = id)
    if method == 'delete':
        if not request.user.has_perm('exmo2010.delete_monitoring', monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        title = _('Delete monitoring %s') % monitoring
        return delete_object(
            request,
            model = Monitoring,
            object_id = id,
            post_delete_redirect = redirect,
            extra_context = {
                'title': title,
                'deleted_objects': Task.objects.filter(organization__monitoring = monitoring),
                }
            )
    elif method == 'calculate': #todo: remove this
        if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        if request.method != 'POST':
            return HttpResponse(_('Only POST allowed'))
        else:
            for task in Task.objects.filter(organization__monitoring = monitoring).select_related(): task.update_openness()
            return HttpResponseRedirect(redirect)
    else: #update
        if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        title = _('Edit monitoring %s') % monitoring
        MonitoringStatusFormset = inlineformset_factory(
            Monitoring,
            MonitoringStatus,
            can_delete = False,
            extra = 0,
            form = MonitoringStatusForm,
            formset = MonitoringStatusBaseFormset,
            )

        if request.method == 'POST':
            form = MonitoringForm(request.POST, instance=monitoring)
            if form.is_valid():
                cd = form.cleaned_data
                m = form.save(commit=False)
                formset = MonitoringStatusFormset(request.POST, instance=m)
                if formset.is_valid():
                    m.save()
                    formset.save()
                    questionnaire = m.get_questionnaire()
                    # Удаление опроса.
                    if cd.get("add_questionnaire") == False and questionnaire:
                        questionnaire.delete()
                    elif cd.get("add_questionnaire") == True and not questionnaire:
                        questionnaire = Questionnaire(monitoring=m)
                        questionnaire.save()
                    return HttpResponseRedirect(redirect)
            else:
                formset = MonitoringStatusFormset(instance=monitoring)
        else:
            form = MonitoringForm(instance=monitoring,
                initial={"add_questionnaire": monitoring.has_questionnaire()})
            formset = MonitoringStatusFormset(instance=monitoring)

        return render_to_response(
            'exmo2010/monitoring_form.html',
            {
                'title': title,
                'form': form,
                'formset': formset,
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
    return render_to_response('exmo2010/monitoring_form.html',
            {'title': title, 'media': form.media, 'form': form,
             'formset': None,}, context_instance=RequestContext(request))



from operator import itemgetter
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

  return render_to_response('exmo2010/rating_color.html', {
        'monitoring': monitoring,
        'object_list': rating_list_with_categories,
        'average': avg,
    }, context_instance=RequestContext(request))



def monitoring_rating(request, m_id):
    """
    Вывод мониторинга
    """
    monitoring = get_object_or_404(Monitoring, pk=m_id)
    if not request.user.has_perm('exmo2010.rating_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))

    has_npa = monitoring.has_npa
    rating_type, parameter_list, form = rating_type_parameter(request,
        monitoring, has_npa)
    rating_list, avg = rating(monitoring, parameters=parameter_list)

    return render_to_response('exmo2010/rating.html', {
        'monitoring': monitoring,
        'has_npa': has_npa,
        'object_list': rating_list,
        'rating_type': rating_type,
        'average': avg,
        'title': _('Rating'),
        'form': form,
    }, context_instance=RequestContext(request))



import tempfile
import copy
import zipfile
import os
from cStringIO import StringIO
@login_required
def monitoring_by_criteria_mass_export(request, id):
    """
    Экспорт по критерию
    Архив из CVS файлов -- по файлу на критерий
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
    Статистика мониторинга по экспертам
    """
    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    experts = Task.objects.filter(organization__monitoring = monitoring).values('user').annotate(cuser=Count('user'))
    title = _('Experts of monitoring %(name)s') % {'name': monitoring.name}
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
    headers=(
          (_('Expert'), 'username', 'username', None, None),
          (_('Open tasks'), 'open_tasks', None, None, None),
          (_('Ready tasks'), 'ready_tasks', None, None, None),
          (_('Approved tasks'), 'approved_tasks', None, None, None),
          (_('All tasks'), 'all_tasks', None, None, None),
          )
    return table(
        request,
        headers,
        queryset = queryset,
        paginate_by = 15,
        extra_context = {
            'monitoring': monitoring,
            'title': title,
            },
        template_name = "exmo2010/expert_list.html",
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

    return render_to_response('exmo2010/monitoring_parameter_filter.html', {
        'form': form,
        'object_list': queryset,
        'monitoring': monitoring,
        'hide': hide
    }, context_instance=RequestContext(request))


@login_required
def monitoring_parameter_found_report(request, id):
    """
    Отчёт по наличию параметра
    """
    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    title = _('Report for %(monitoring)s by parameter and found') % { 'monitoring': monitoring }
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
    return render_to_response('exmo2010/monitoring_parameter_found_report.html', {
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
    Экспорт организаций в CSV
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
    Импорт организаций из CSV
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

    return render_to_response('exmo2010/monitoring_import_log.html', {
      'monitoring': monitoring,
      'file': request.FILES['orgfile'],
      'errLog': errLog,
      'rowOKCount': rowOKCount,
      'rowALLCount': rowALLCount,
      'title': title
    }, context_instance=RequestContext(request))



@login_required
@csrf_protect
def monitoring_parameter_import(request, id):
    """
    Импорт параметров из CSV
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
            if row[1]  == '':
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

    return render_to_response('exmo2010/monitoring_import_log.html', {
      'monitoring': monitoring,
      'file': request.FILES['paramfile'],
      'errLog': errLog,
      'rowOKCount': rowOKCount,
      'rowALLCount': rowALLCount,
      'title': title
    }, context_instance=RequestContext(request))



@login_required
@csrf_protect
def monitoring_comment_report(request, id):
    monitoring = get_object_or_404(Monitoring, pk=id)
    time_to_answer = monitoring.time_to_answer
    if not (request.user.profile.is_expertA or request.user.is_superuser):
        return HttpResponseForbidden(_('Forbidden'))

    from django.contrib.comments import models as commentModel
    from datetime import datetime, timedelta
    from exmo2010.forms import MonitoringCommentStatForm

    form = MonitoringCommentStatForm(
        monitoring=monitoring,
        initial= {'time_to_answer': time_to_answer})

    start_date = MonitoringStatus.objects.get(
        monitoring=monitoring,
        status=Monitoring.MONITORING_INTERACT).start
    if not start_date:
        return render_to_response(
            "msg.html", {
                'msg': _('Start date for interact not defined.')
            }, context_instance=RequestContext(request))
    end_date = datetime.today()

    if request.method == "GET" and request.GET.__contains__('time_to_answer'):
        form = MonitoringCommentStatForm(request.GET, monitoring=monitoring)
        if form.is_valid():
            time_to_answer = int(form.cleaned_data['time_to_answer'])
            if time_to_answer != monitoring.time_to_answer:
                monitoring.time_to_answer = time_to_answer
                monitoring.save()

    comments_without_reply = []
    fail_comments_without_reply = []
    comments_with_reply = []
    fail_soon_comments_without_reply = []
    fail_comments_with_reply = []
    org_comments = []
    active_organizations = []
    active_organization_stats = []
    active_iifd_person_stats = []
    iifd_all_comments = []

    if (request.user.has_perm('exmo2010.admin_monitoring', monitoring) or
        request.user.profile.is_expertA):
        scores = Score.objects.filter(
            task__organization__monitoring=monitoring)

    if start_date:
        total_org = Organization.objects.filter(monitoring=monitoring)
        reg_org = total_org.filter(userprofile__isnull=False)
        iifd_all_comments = commentModel.Comment.objects.filter(
            content_type__model='score',
            submit_date__gte=start_date,
            object_pk__in=Score.objects.filter(
                task__organization__monitoring=monitoring),
            user__in=User.objects.exclude(
                groups__name='organizations')).order_by('submit_date')

        org_comments = commentModel.Comment.objects.filter(
            content_type__model='score',
            submit_date__gte=start_date,
            object_pk__in=scores,
            user__in=User.objects.filter(
                groups__name='organizations')).order_by('submit_date')
        org_all_comments=commentModel.Comment.objects.filter(
            content_type__model='score',
            submit_date__gte=start_date,
            object_pk__in=Score.objects.filter(
                task__organization__monitoring=monitoring),
            user__in=User.objects.filter(
                groups__name='organizations')).order_by('submit_date')

        active_organizations = set([Score.objects.get(
            pk=oco.object_pk).task.organization for oco in org_all_comments])
        for active_organization in active_organizations:
            active_org_comments_count = org_comments.filter(
                object_pk__in=Score.objects.filter(
                    task__organization__monitoring=monitoring,
                    task__organization=active_organization)).count()

            active_organization_stats.append(
                {'org': active_organization,
                 'comments_count': active_org_comments_count})

        active_iifd_person_stats = User.objects.filter(
            comment_comments__pk__in=iifd_all_comments).annotate(
            comments_count=Count('comment_comments'))


    for org_comment in org_comments:
        from exmo2010.utils import workday_count
        iifd_comments = iifd_all_comments.filter(
            submit_date__gte=org_comment.submit_date,
            object_pk=org_comment.object_pk,
        ).order_by('submit_date')
        #append comment or not
        delta = timedelta(days=1)
        flag = False
        for iifd_comment in iifd_comments:
            #check that comment from iifd comes after organization
            if iifd_comment.submit_date > org_comment.submit_date:
                #iifd comment comes in time_to_answer
                if workday_count(org_comment.submit_date,
                                 iifd_comment.submit_date) <= time_to_answer:
                    #pass that this org_comment is with reply
                    flag = True
                    comments_with_reply.append(org_comment)
                    break
                #iifd comment comes out of time_to_answer
                elif workday_count(org_comment.submit_date,
                                   iifd_comment.submit_date) > time_to_answer:
                    #pass that this org_comment is with reply
                    flag = True
                    fail_comments_with_reply.append(org_comment)
                    break
                    #org comment is without comment from iifd
        if not flag:
            #check time_to_answer
            if workday_count(org_comment.submit_date.date() + delta,
                             end_date) == time_to_answer:
                fail_soon_comments_without_reply.append(org_comment)
            elif workday_count(org_comment.submit_date.date() + delta,
                               end_date) > time_to_answer:
                fail_comments_without_reply.append(org_comment)
            else:
                comments_without_reply.append(org_comment)

    return render_to_response('exmo2010/monitoring_comment_report.html', {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'comments_without_reply': comments_without_reply,
        'fail_comments_without_reply': fail_comments_without_reply,
        'fail_soon_comments_without_reply': fail_soon_comments_without_reply,
        'fail_comments_with_reply': fail_comments_with_reply,
        'comments_with_reply': comments_with_reply,
        'org_comments': org_comments,
        'iifd_comments': iifd_all_comments,
        'active_organization_stats': active_organization_stats,
        'total_org': total_org.count(),
        'reg_org': reg_org.count(),
        'active_iifd_person_stats': active_iifd_person_stats,
        'time_to_answer': time_to_answer,
        'monitoring': monitoring,
        'title': _('Comment report for %(monitoring)s') % { 'monitoring': monitoring,},
        'media': CORE_MEDIA,
        }, context_instance=RequestContext(request))


@csrf_exempt
def add_questionnaire(request, m_id):
    """
    Создание опросника анкеты мониторинга.
    Формат входящего json-файла (уже дисериализованного):
    [
     "Название анкеты",
     "Примечание к анкете",
     [
      ("Текст вопроса", "Пояснение к вопросу", 0, []),
      ("Текст вопроса2", "", 1, []),
      ("Текст вопроса3", "Пояснение к вопросу3", 2, ["Первый вариант ответа",
       "Второй вариант ответа", "Третий вариант ответа"]),
     ]
    ]
    """
    monitoring = get_object_or_404(Monitoring, pk=m_id)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    if monitoring.has_questions():
        return HttpResponseForbidden(_('Forbidden'))
    if request.method == "POST":
        if request.is_ajax():
            questionset_json = request.POST.get("questionaire")
            try:
                questionset = simplejson.loads(questionset_json)
            except simplejson.JSONDecodeError:
                questionset = None
            if questionset:
                a_name, a_comm, qlist = questionset
                questionnaire = Questionnaire.objects.get_or_create(
                    monitoring=monitoring)[0]
                questionnaire.title = a_name
                questionnaire.comment = a_comm
                questionnaire.save()
                for q in qlist:
                    q_question, q_comment, q_type, q_a_variants = q
                    new_question = QQuestion(questionnaire=questionnaire)
                    new_question.qtype = int(q_type)
                    new_question.question = q_question
                    if q_comment:
                        new_question.comment = q_comment
                    new_question.save()
                    if int(q_type) == 2:  # Выбор варианта ответа.
                        for a in q_a_variants:
                            new_answer = AnswerVariant(qquestion=new_question)
                            new_answer.answer = a
                            new_answer.save()
            return HttpResponse("Опросник создан!")
        else:
            return HttpResponseForbidden(_('Forbidden'))
    else:
        title = _('Edit monitoring %s') % monitoring
        # title0 - потому что переменную title ждет темплейт base.html и
        # использует не так, как мне тут нужно.
        return render_to_response('exmo2010/add_questionnaire.html',
            {"monitoring": monitoring, "title0": title},
            context_instance=RequestContext(request))


def get_qq(request):
    """AJAX-вьюха для получения кода div'а для одного вопроса (c полями)"""
    if request.method == "GET" and request.is_ajax():
        return render_to_response('exmo2010/forms/question_div.html',
            {"choices": QUESTION_TYPE_CHOICES,},
            context_instance=RequestContext(request))
    else:
        raise Http404


def get_qqt(request):
    """AJAX-вьюха для получения кода div'а для одного вопроса (без полей)"""
    if request.method == "GET" and request.is_ajax():
        return render_to_response('exmo2010/forms/question_div2.html',
            context_instance=RequestContext(request))
    else:
        raise Http404

@csrf_exempt
def get_pc(request):
    """AJAX-вьюха для получения списка критериев, отключенных у параметра"""
    if request.user.is_authenticated() and request.method == "POST" and \
       request.is_ajax():
        try:
            parameter = Parameter.objects.get(pk=request.POST.get("p_id"))
        except ObjectDoesNotExist:
            raise Http404
        skip_list = []
        if not parameter.complete:
            skip_list.append(2)
        if not parameter.topical:
            skip_list.append(3)
        if not parameter.accessible:
            skip_list.append(4)
        if not parameter.hypertext:
            skip_list.append(5)
        if not parameter.document:
            skip_list.append(6)
        if not parameter.image:
            skip_list.append(7)

        return HttpResponse(simplejson.dumps(skip_list),
            mimetype='application/json')
    else:
        raise Http404
