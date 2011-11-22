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
from reversion import revision

def monitoring_list(request):
    monitorings_pk = []
    for m in Monitoring.objects.all().select_related():
        if request.user.has_perm('exmo2010.view_monitoring', m):
            monitorings_pk.append(m.pk)
    if not monitorings_pk and not request.user.has_perm('exmo2010.create_monitoring', Monitoring()): return HttpResponseForbidden(_('Forbidden'))
    queryset = Monitoring.objects.filter(pk__in = monitorings_pk)
    headers =   (
                (_('monitoring'), 'name', 'name', None, None),
                (_('status'), 'status', 'status', int, Monitoring.MONITORING_STATUS_FULL),
                )
    return table(
        request,
        headers,
        queryset = queryset,
        paginate_by = 15,
        extra_context = {
            'title': _('Monitoring list'),
            'fakeobject': Monitoring(),
        },
    )



@login_required
def monitoring_manager(request, id, method):
    redirect = '%s?%s' % (reverse('exmo.exmo2010.view.monitoring.monitoring_list'), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    if method == 'delete':
        monitoring = get_object_or_404(Monitoring, pk = id)
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
    else: #update
        monitoring = get_object_or_404(Monitoring, pk = id)
        if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        title = _('Edit monitoring %s') % monitoring
        from django.forms.models import inlineformset_factory
        MonitoringStatusFormset = inlineformset_factory(
            Monitoring,
            MonitoringStatus,
            can_delete = False,
            extra = 0,
            form = MonitoringStatusForm,
            )

        form = MonitoringForm(instance = monitoring)
        formset = MonitoringStatusFormset(instance = monitoring)

        if request.method == 'POST':
            form = MonitoringForm(request.POST, instance = monitoring)
            if form.is_valid():
                m = form.save(commit = False)
                formset = MonitoringStatusFormset(request.POST, instance = m)
                if formset.is_valid():
                    m.save()
                    formset.save()
                    return HttpResponseRedirect(redirect)

        return render_to_response(
            'exmo2010/monitoring_form.html',
            {
                'title': title,
                'form': form,
                'formset': formset,
                'media': CORE_MEDIA+formset.media,
                'object': monitoring,
            },
            context_instance=RequestContext(request))

@login_required
def monitoring_add(request):
    if not request.user.has_perm('exmo2010.create_monitoring', Monitoring()):
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
      writer[criteria] = csv.writer(handle[criteria])
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



from exmo.exmo2010.forms import ParameterFilterForm
@login_required
def monitoring_parameter_filter(request, id):
    monitoring = get_object_or_404(Monitoring, pk = id)
    if not (request.user.profile.is_expert or request.user.is_superuser):
        return HttpResponseForbidden(_('Forbidden'))
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
                task__organization__monitoring = monitoring,
                parameter = parameter,
                found = form.cleaned_data['found'],
            ).exclude(
                task__organization__in = parameter.exclude.all(),
            )
            if request.user.has_perm('exmo2010.admin_monitoring', monitoring):
                queryset = queryset.filter(task__status = Task.TASK_APPROVED)
            elif request.user.profile.is_expertB:
                queryset = queryset.filter(task__status = Task.TASK_CLOSED)
    return render_to_response('exmo2010/monitoring_parameter_filter.html', {
        'form': form,
        'object_list': queryset,
        'title': title,
        'monitoring': monitoring,
    }, context_instance=RequestContext(request))



@login_required
def monitoring_parameter_found_report(request, id):
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



import csv
@login_required
def monitoring_parameter_export(request, id):

    def safeConvert(string):
      if string:
        return string.encode("utf-8")
      else:
        return ''

    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    parameters = Parameter.objects.filter(monitoring = monitoring)
    response = HttpResponse(mimetype = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=monitoring-parameters-%s.csv' % id
    writer = csv.writer(response)
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
            p.name.encode("utf-8"),
            safeConvert(p.description),
            int(p.complete),
            int(p.topical),
            int(p.accessible),
            int(p.hypertext),
            int(p.document),
            int(p.image),
            p.weight
        )
        keywords = ", ".join([k.name for k in p.tags])
        out += (safeConvert(keywords),)
        writer.writerow(out)
    return response



@login_required
def monitoring_organization_export(request, id):

    def safeConvert(string):
      if string:
        return string.encode("utf-8")
      else:
        return ''

    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    organizations = Organization.objects.filter(monitoring = monitoring)
    response = HttpResponse(mimetype = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=monitoring-orgaization-%s.csv' % id
    writer = csv.writer(response)
    writer.writerow([
        '#Name',
        'Url',
        'Comments',
        'Keywords',
    ])
    for o in organizations:
        out = (
            o.name.encode("utf-8"),
            o.url.encode("utf-8"),
            safeConvert(o.comments),
        )
        keywords = ", ".join([k.name for k in o.tags])
        out += (safeConvert(keywords),)
        writer.writerow(out)
    return response



@revision.create_on_success
@login_required
@csrf_protect
def monitoring_organization_import(request, id):
    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    if not request.FILES.has_key('orgfile'):
        return HttpResponseRedirect(reverse('exmo.exmo2010.view.monitoring.monitoring_list'))
    reader = csv.reader(request.FILES['orgfile'])
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
                name = str(row[0]).strip().decode('utf-8')
                organization = Organization.objects.get(monitoring = monitoring, name = name)
            except Organization.DoesNotExist:
                organization = Organization()
                organization.monitoring = monitoring
            except Exception, e:
                errLog.append("row %d. %s" % (reader.line_num, e))
                continue
            try:
                organization.name = name
                organization.url = str(row[1]).strip()
                organization.comments = str(row[2]).strip().decode('utf-8')
                organization.keywords = str(row[3]).strip().decode('utf-8')
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
    return render_to_response('exmo2010/monitoring_import_log.html', {
      'monitoring': monitoring,
      'file': request.FILES['orgfile'],
      'errLog': errLog,
      'rowOKCount': rowOKCount,
      'rowALLCount': rowALLCount,
      'title': title
    }, context_instance=RequestContext(request))



@revision.create_on_success
@login_required
@csrf_protect
def monitoring_parameter_import(request, id):
    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    if not request.FILES.has_key('paramfile'):
        return HttpResponseRedirect(reverse('exmo.exmo2010.view.monitoring.monitoring_list'))
    reader = csv.reader(request.FILES['paramfile'])
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
                code = int(row[0])
                name = str(row[1]).strip().decode('utf-8')
                parameter = Parameter.objects.get(monitoring = monitoring, code = code, name = name)
            except Parameter.DoesNotExist:
                parameter = Parameter()
            except Exception, e:
                errLog.append("row %d. %s" % (reader.line_num, e))
                continue
            try:
                parameter.monitoring = monitoring
                parameter.code = code
                parameter.name = name
                parameter.description = str(row[2]).strip().decode('utf-8')
                parameter.complete = bool(int(row[3]))
                parameter.topical = bool(int(row[4]))
                parameter.accessible = bool(int(row[5]))
                parameter.hypertext = bool(int(row[6]))
                parameter.document = bool(int(row[7]))
                parameter.image = bool(int(row[8]))
                parameter.weight = int(row[9])
                parameter.keywords = str(row[10]).strip().decode('utf-8')
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
    monitoring = get_object_or_404(Monitoring, pk = id)
    if not (request.user.profile.is_expert or request.user.is_superuser):
        return HttpResponseForbidden(_('Forbidden'))

    from django.contrib.comments import models as commentModel
    from django.contrib.sites import models as sitesModel
    from datetime import datetime, timedelta
    from django.db.models import Q
    from exmo.exmo2010.forms import MonitoringCommentStatForm

    form = MonitoringCommentStatForm(monitoring = monitoring)

    start_date = MonitoringStatus.objects.get(monitoring = monitoring, status = Monitoring.MONITORING_INTERACT).start
    if not start_date:
        return render_to_response(
            "msg.html", {
                'msg': _('Start date for interact not defined.')
                }, context_instance=RequestContext(request))
    end_date = datetime.now()

    limit = 2
    if request.method == "GET" and request.GET.__contains__('limit'):
        form = MonitoringCommentStatForm(request.GET, monitoring = monitoring)
        if form.is_valid():
            limit = form.cleaned_data['limit']

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

    if request.user.has_perm('exmo2010.admin_monitoring') or request.user.profile.is_expertA:
        scores = Score.objects.filter(task__organization__monitoring = monitoring)
    elif request.user.profile.is_expertB:
        scores = Score.objects.filter(task__organization__monitoring = monitoring, task__user = request.user)

    if start_date:
        total_org = Organization.objects.filter(monitoring = monitoring)
        reg_org = total_org.filter(userprofile__isnull = False)
        iifd_all_comments = commentModel.Comment.objects.filter(
            content_type__model = 'score',
            submit_date__gte = start_date,
            object_pk__in = Score.objects.filter(task__organization__monitoring = monitoring ),
            user__in = User.objects.exclude(groups__name = 'organizations')).order_by('submit_date')

        org_comments = commentModel.Comment.objects.filter(
            content_type__model = 'score',
            submit_date__gte = start_date,
            object_pk__in = scores,
            user__in = User.objects.filter(groups__name = 'organizations')).order_by('submit_date')
        org_all_comments = commentModel.Comment.objects.filter(
            content_type__model = 'score',
            submit_date__gte = start_date,
            object_pk__in = Score.objects.filter(task__organization__monitoring = monitoring),
            user__in = User.objects.filter(groups__name = 'organizations')).order_by('submit_date')

        active_organizations = set([Score.objects.get(pk = oco.object_pk).task.organization for oco in org_all_comments])
        for active_organization in active_organizations:
            active_org_comments_count = org_comments.filter(
                object_pk__in = Score.objects.filter(task__organization__monitoring = monitoring, task__organization = active_organization)
            ).count()
            active_organization_stats.append({ 'org': active_organization, 'comments_count': active_org_comments_count})

        active_iifd_person_stats = User.objects.filter(comment_comments__pk__in = iifd_all_comments).annotate(comments_count = Count('comment_comments'))


    for org_comment in org_comments:
        from exmo.helpers import workday_count
        iifd_comments = iifd_all_comments.filter(
            submit_date__gte = org_comment.submit_date,
            object_pk = org_comment.object_pk,
        ).order_by('submit_date')
        #append comment or not
        flag = False
        for iifd_comment in iifd_comments:
            #check that comment from iifd comes after organization
            if iifd_comment.submit_date > org_comment.submit_date:
                #iifd comment comes in limit
                if workday_count(org_comment.submit_date, iifd_comment.submit_date) <= limit:
                    #pass that this org_comment is with reply
                    flag = True
                    comments_with_reply.append(org_comment)
                    break
                #iifd comment comes out of limit
                elif workday_count(org_comment.submit_date, iifd_comment.submit_date) > limit:
                    #pass that this org_comment is with reply
                    flag = True
                    fail_comments_with_reply.append(org_comment)
                    break
        #org comment is without comment from iifd
        if not flag:
            #check limit
            if limit-1 < workday_count(org_comment.submit_date, end_date) <= limit:
                fail_soon_comments_without_reply.append(org_comment)
            elif workday_count(org_comment.submit_date, end_date) > limit:
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
        'limit': limit,
        'monitoring': monitoring,
        'title': _('Comment report for %(monitoring)s') % { 'monitoring': monitoring, },
        'media': CORE_MEDIA,
        }, context_instance=RequestContext(request))
