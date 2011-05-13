# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 Institute for Information Freedom Development
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
from exmo.exmo2010.view.helpers import table
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import update_object, create_object, delete_object
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from exmo.exmo2010.models import Organization, Parameter, Score, Task
from exmo.exmo2010.models import Monitoring, Claim
from exmo.exmo2010.models import MonitoringStatus
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models import Count
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.template import RequestContext
from django.views.decorators.cache import cache_page
from django.core.urlresolvers import reverse
from exmo.exmo2010.forms import MonitoringForm, MonitoringStatusForm, CORE_MEDIA

def monitoring_list(request):
    monitorings_pk = []
    for m in Monitoring.objects.all():
        if request.user.has_perm('exmo2010.view_monitoring', m):
            monitorings_pk.append(m.pk)
    if not monitorings_pk: return HttpResponseForbidden(_('Forbidden'))
    queryset = Monitoring.objects.filter(pk__in = monitorings_pk)
    headers =   (
                (_('Monitoring'), 'name', 'name', None, None),
                )
    return table(
        request,
        headers,
        queryset = queryset,
        paginate_by = 15,
        extra_context = {
            'title': _('Monitoring list')
        },
    )



@login_required
def monitoring_manager(request, id, method):
    if not request.user.is_superuser:
        return HttpResponseForbidden(_('Forbidden'))
    redirect = '%s?%s' % (reverse('exmo.exmo2010.view.monitoring.monitoring_list'), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    if method == 'add':
        return monitoring_add(request)
    elif method == 'delete':
        monitoring = get_object_or_404(Monitoring, pk = id)
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
    else: #update
        monitoring = get_object_or_404(Monitoring, pk = id)
        title = _('Edit monitoring %s') % monitoring
        from django.forms.models import inlineformset_factory
        MonitoringStatusFormset = inlineformset_factory(
            Monitoring,
            MonitoringStatus,
            can_delete = False,
            extra = 0,
            form = MonitoringStatusForm,
            )
        if request.method == 'POST':
            form = MonitoringForm(request.POST, instance = monitoring)
            if form.is_valid():
                m = form.save()
                return HttpResponseRedirect(redirect)
        form = MonitoringForm(instance = monitoring)
        formset = MonitoringStatusFormset(instance = monitoring)
        return render_to_response(
            'exmo2010/monitoring_form.html',
            {
                'title': title,
                'form': form,
                'formset': formset,
                'media': CORE_MEDIA+formset.media,
            },
            context_instance=RequestContext(request))

@login_required
def monitoring_add(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden(_('Forbidden'))
    title = _('Add new monitoring')
    if request.method == 'POST':
        form = MonitoringForm(request.POST)
        if form.is_valid:
            monitoring_instance = form.save()
            monitoring_instance.create_calendar()
            redirect = reverse('exmo.exmo2010.view.monitoring.monitoring_manager', args=[monitoring_instance.pk, 'update'])
            return HttpResponseRedirect(redirect)
    else:
        form = MonitoringForm()
        form.fields['status'].choices = Monitoring.MONITORING_STATUS_NEW
    return render_to_response(
        'exmo2010/monitoring_form.html',
        {
            'title': title,
            'media': form.media,
            'form': form,
            'formset': None,
        },
        context_instance=RequestContext(request))



from operator import itemgetter
#update rating twice in a day
#@cache_page(60 * 60 * 12)
def monitoring_rating(request, id):
  monitoring = get_object_or_404(Monitoring, pk = id)
  if not request.user.has_perm('exmo2010.rating_monitoring', monitoring): return HttpResponseForbidden(_('Forbidden'))
  object_list = [{'task':task, 'openness': task.openness} for task in Task.approved_tasks.filter(organization__monitoring = monitoring).order_by('-openness_cache')]
  place=1
  avg=None
  if object_list:
    max_rating = object_list[0]['openness']
    avg = sum([t['openness'] for t in object_list])/len(object_list)
  rating_list = []
  for rating_object in object_list:
    if rating_object['openness'] < max_rating:
        place+=1
        max_rating = rating_object['openness']
    rating = [rating_object, place ]
    rating_list.append(rating)

  return render_to_response('exmo2010/rating.html', {
        'monitoring': monitoring,
        'object_list': rating_list,
        'average': avg,
    }, context_instance=RequestContext(request))



import tempfile
import copy
import zipfile
import os
import csv
from cStringIO import StringIO
@login_required
def monitoring_by_criteria_mass_export(request, id):

    def safeConvert(string):
      if string:
        return string.encode("utf-8")
      else:
        return ''

    if not request.user.is_superuser: # TODO: check_permission
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk = id)
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
      writer[criteria] = csv.writer(handle[criteria])
    header_row = True
    parameters = Parameter.objects.filter(monitoring = monitoring)
    for task in Task.approved_tasks.filter(monitoring = monitoring):
      row = copy.deepcopy(row_template)
      if header_row:
        for criteria in row.keys():
          row[criteria] = [''] + [ p.fullcode() for p in parameters ]
          writer[criteria].writerow(row[criteria])
        header_row = False
        row = copy.deepcopy(row_template)
      for criteria in row.keys():
        row[criteria] = [safeConvert(task.organization.name)]
      for parameter in parameters:
        try:
          score = Score.objects.filter(task = task).filter(parameter = parameter)[0]
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
          if score.parameter.complete:
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
    if not request.user.is_superuser: return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk = id)
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



@login_required
def monitoring_info(request, id):
    if not request.user.is_superuser: return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk = id)
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



from exmo.exmo2010.forms import ParameterFilterForm
@login_required
def monitoring_parameter_filter(request, id):
    if not request.user.is_superuser: return HttpResponseForbidden(_('Forbidden'))
    title = _('Parameter-criteria filter')
    monitoring = get_object_or_404(Monitoring, pk = id)
    form = ParameterFilterForm()
    form.fields['parameter'].queryset = Parameter.objects.filter(monitoring = monitoring)
    queryset = None
    if request.GET.__contains__("parameter"):
        form = ParameterFilterForm(request.GET)
        form.fields['parameter'].queryset = Parameter.objects.filter(monitoring = monitoring)
        if form.is_valid():
            parameter = form.cleaned_data['parameter']
            queryset = Score.objects.filter(
                task__monitoring = monitoring,
                parameter = parameter,
                found = form.cleaned_data['found'],
                task__status = Task.TASK_APPROVED
            ).exclude(
                task__organization__in = parameter.exclude.all(),
            )
    return render_to_response('exmo2010/monitoring_parameter_filter.html', {
        'form': form,
        'object_list': queryset,
        'title': title,
        'monitoring': monitoring,
    }, context_instance=RequestContext(request))



@login_required
def monitoring_parameter_found_report(request, id):
    if not request.user.is_superuser: return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk = id)
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
    score_count_category = 0
    score_count_subcategory = 0
    organization_count_category = 0
    organization_count_subcategory = 0
    queryset_list = list(queryset)
    for parameter in queryset_list:
        try:
            next_parameter = queryset_list[queryset_list.index(parameter)+1]
        except:
            next_parameter = None
        score_count_category_public = None
        score_count_subcategory_public = None
        organization_count_category_public = None
        organization_count_subcategory_public = None
        score_per_organization_category = None
        score_per_organization_subcategory = None
        score_count = Score.objects.filter(
            task__monitoring = monitoring,
            task__status = Task.TASK_APPROVED,
            found = 1,
            parameter = parameter,
        ).exclude(
            task__organization__in = parameter.exclude.all(),
        ).count()
        score_count_total += score_count
        organization_count_total += parameter.organization_count
        score_per_organization = float(score_count) / parameter.organization_count * 100
        score_count_category += score_count
        score_count_subcategory += score_count
        organization_count_category += parameter.organization_count
        organization_count_subcategory += parameter.organization_count
        if next_parameter:
            if next_parameter.group.group != parameter.group.group:
                score_count_category_public = score_count_category
                score_count_category = 0
                organization_count_category_public = organization_count_category
                organization_count_category = 0
                score_per_organization_category = float(score_count_category_public) / organization_count_category_public * 100
            if next_parameter.group != parameter.group:
                score_count_subcategory_public = score_count_subcategory
                score_count_subcategory = 0
                organization_count_subcategory_public = organization_count_subcategory
                organization_count_subcategory = 0
                score_per_organization_subcategory = float(score_count_subcategory_public) / organization_count_subcategory_public * 100
        else:
            score_count_category_public = score_count_category
            score_count_category = 0
            organization_count_category_public = organization_count_category
            organization_count_category = 0
            score_per_organization_category = float(score_count_category_public) / organization_count_category_public * 100
            score_count_subcategory_public = score_count_subcategory
            score_count_subcategory = 0
            organization_count_subcategory_public = organization_count_subcategory
            organization_count_subcategory = 0
            score_per_organization_subcategory = float(score_count_subcategory_public) / organization_count_subcategory_public * 100
        obj = {
            'parameter': parameter,
            'organization_count': parameter.organization_count,
            'score_count': score_count,
            'score_per_organization': score_per_organization,
            'score_count_category': score_count_category_public,
            'score_count_subcategory': score_count_subcategory_public,
            'organization_count_category': organization_count_category_public,
            'organization_count_subcategory': organization_count_subcategory_public,
            'score_per_organization_category': score_per_organization_category,
            'score_per_organization_subcategory': score_per_organization_subcategory,
        }
        object_list.append(obj)
    score_per_organization_total = float(score_count_total) / organization_count_total * 100
    return render_to_response('exmo2010/monitoring_parameter_found_report.html', {
        'monitoring': monitoring,
        'title': title,
        'object_list': object_list,
        'score_count_total': score_count_total,
        'organization_count_total': organization_count_total,
        'score_per_organization_total': score_per_organization_total,
    }, context_instance=RequestContext(request))
