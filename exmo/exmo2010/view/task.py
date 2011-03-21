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
from exmo.exmo2010.forms import TaskForm
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import update_object, create_object, delete_object
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from exmo.exmo2010.models import Organization, Parameter, Score, Task, Category, Subcategory
from exmo.exmo2010.models import Monitoring, Claim
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models import Count
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.views.decorators.cache import cache_page
from django.http import HttpResponseForbidden
from django.core.urlresolvers import reverse
from reversion import revision



import csv
from django.http import HttpResponse
@login_required
def task_export(request, id):

    def safeConvert(string):
      if string:
        return string.encode("utf-8")
      else:
        return ''

    task = get_object_or_404(Task, pk = id)
    if not request.user.has_perm('exmo2010.view_task', task):
        return HttpResponseForbidden(_('Forbidden'))
    parameters = Parameter.objects.filter(monitoring = task.monitoring).exclude(exclude = task.organization)
    scores     = Score.objects.filter(task = id)
    response = HttpResponse(mimetype = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=task-%s.csv' % id
    writer = csv.writer(response)
    writer.writerow([
        'Code',
        'Name',
        'Type',
        'Found',
        'Complete',
        'CompleteComment',
        'Topical',
        'TopicalComment',
        'Accessible',
        'AccessibleComment',
        'Hypertext',
        'HypertextComment',
        'Document',
        'DocumentComment',
        'Image',
        'ImageComment',
        'Comment'
    ])
    category = None
    subcategory = None
    for p in parameters:
        if p.group.group.code != category:
          category = p.group.group.code
          out = (p.group.group.code, p.group.group.name.encode("utf-8"))
          writer.writerow(out)
        if p.group.code != subcategory:
          subcategory = p.group.code
          out = (p.group.fullcode(), p.group.name.encode("utf-8"))
          writer.writerow(out)
        out = (
            p.fullcode(),
            p.name.encode("utf-8"),
            p.type.name.encode("utf-8")
        )
        try:
            s = scores.get(parameter = p)
        except:
            out += (
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                ''
            )
        else:
            out += (s.found,)
            if p.type.complete:
                out += (
                    s.complete,
                    safeConvert(s.completeComment))
            else:
                out += ('','')
            if p.type.topical:
                out += (
                    s.topical,
                    safeConvert(s.topicalComment))
            else:
                out += ('','')
            if p.type.accessible:
                out += (
                    s.accessible,
                    safeConvert(s.accessibleComment))
            else:
                out += ('','')
            if p.type.hypertext:
                out += (
                    s.hypertext,
                    safeConvert(s.hypertextComment))
            else:
                out += ('','')
            if p.type.document:
                out += (
                    s.document,
                    safeConvert(s.documentComment))
            else:
                out += ('','')
            if p.type.image:
                out += (
                s.image,
                safeConvert(s.imageComment))
            else:
                out += ('','')
            out += (safeConvert(s.comment),)
        writer.writerow(out)
    return response



import re
@revision.create_on_success
@login_required
def task_import(request, id):

    def safeConvert(string, toType):
        if string:
            return toType(string)
        else:
            return None

    task = get_object_or_404(Task, pk = id)
    if not request.user.has_perm('exmo2010.fill_task', task):
        return HttpResponseForbidden(_('Forbidden'))
    if not request.FILES.has_key('taskfile'):
        return HttpResponseRedirect(reverse('exmo.exmo2010.view.score.score_list_by_task', args=[id]))
    reader = csv.reader(request.FILES['taskfile'])
    errLog = []
    rowOKCount = 0
    rowALLCount = 0
    try:
        for row in reader:
            rowALLCount += 1
            try:
                code = re.match('^(\d+)\.(\d+)\.(\d+)$', row[0])
                if not code:
                  errLog.append("row %d (csv). Not a code: %s" % (reader.line_num, row[0]))
                  continue
                if (
                    row[3]  == '' and
                    row[4]  == '' and
                    row[5]  == '' and
                    row[6]  == '' and
                    row[7]  == '' and
                    row[8]  == '' and
                    row[9]  == '' and
                    row[10] == '' and
                    row[11] == '' and
                    row[12] == '' and
                    row[13] == '' and
                    row[14] == '' and
                    row[15] == '' and
                    row[16] == ''
                  ):
                    errLog.append("row %d (csv). Empty score: %s" % (reader.line_num, row[0]))
                    continue
                parameter = Parameter.objects.filter(group__group__code=code.group(1)).filter(group__code=code.group(2)).get(code=code.group(3))
                try:
                    score = Score.objects.get(task = task, parameter = parameter)
                except Score.DoesNotExist:
                    score = Score()
                score.task              = task
                score.parameter         = parameter
                score.found             = safeConvert(row[3], int)
                score.complete          = safeConvert(row[4], int)
                score.completeComment   = safeConvert(row[5], str)
                score.topical           = safeConvert(row[6], int)
                score.topicalComment    = safeConvert(row[7], str)
                score.accessible        = safeConvert(row[8], int)
                score.accessibleComment = safeConvert(row[9], str)
                score.hypertext         = safeConvert(row[10], int)
                score.hypertextComment  = safeConvert(row[11], str)
                score.document          = safeConvert(row[12], int)
                score.documentComment   = safeConvert(row[13], str)
                score.image             = safeConvert(row[14], int)
                score.imageComment      = safeConvert(row[15], str)
                score.comment           = safeConvert(row[16], str)
                score.full_clean()
                score.save()
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
    title = _('Import CSV for task %s') % task
    return render_to_response('exmo2010/task_import_log.html', {
      'task': task,
      'file': request.FILES['taskfile'],
      'errLog': errLog,
      'rowOKCount': rowOKCount,
      'rowALLCount': rowALLCount,
      'title': title
    })



def tasks(request):
    return HttpResponseRedirect(reverse('exmo.exmo2010.view.monitoring.monitoring_list'))



def tasks_by_monitoring_and_organization(request, monitoring_id, organization_id):
    '''We have 3 generic group: experts, customers, organizations.
    Superusers: all tasks
    Experts: only own tasks
    Customers: all approved tasks
    organizations: all approved tasks of organizations that belongs to user
    Also for every ogranization we can have group'''
    monitoring = get_object_or_404(Monitoring, pk = monitoring_id)
    organization = get_object_or_404(Organization, pk = organization_id, type = monitoring.type)
    user = request.user
    profile = None
    if user.is_active: profile = user.get_profile()
    if not user.has_perm('exmo2010.view_monitoring', monitoring): return HttpResponseForbidden(_('Forbidden'))
    title = _('Task list for %s') % organization.name
    queryset = Task.objects.filter(monitoring = monitoring, organization = organization)
    # Or, filtered by user
    if user.is_superuser:
      headers = (
                (_('Organization'), 'organization__name', 'organization__name', None, None),
                (_('Expert'), 'user__username', 'user__username', None, None),
                (_('Status'), 'status', 'status', int, Task.TASK_STATUS),
                (_('Complete, %'), 'complete', None, None, None),
                (_('Openness, %'), None, None, None, None),
              )
    elif profile and profile.is_expert:
    # Or, without Expert
      headers = (
                (_('Organization'), 'organization__name', 'organization__name', None, None),
                (_('Status'), 'status', 'status', int, Task.TASK_STATUS),
                (_('Complete, %'), 'complete', None, None, None),
                (_('Openness, %'), None, None, None, None)
              )
    else:
      queryset = Task.approved_tasks.all()
      queryset = queryset.filter(monitoring = monitoring, organization = organization)
      headers = (
                (_('Organization'), 'organization__name', 'organization__name', None, None),
                (_('Complete, %'), 'complete', None, None, None),
                (_('Openness, %'), None, None, None, None)
              )
    task_list = []
    for task in queryset:
        if user.has_perm('exmo2010.view_task', task): task_list.append(task.pk)
    queryset = Task.objects.filter(pk__in = task_list).extra(select = {'complete': Task._complete})
    return table(request, headers, queryset = queryset, paginate_by = 15, extra_context = {'monitoring': monitoring, 'organization': organization, 'title': title })



@revision.create_on_success
@login_required
def task_add(request, monitoring_id, organization_id=None):
    monitoring = get_object_or_404(Monitoring, pk = monitoring_id)
    if organization_id:
        organization = get_object_or_404(Organization, pk = organization_id, type = monitoring.type)
        redirect = '%s?%s' % (reverse('exmo.exmo2010.view.task.tasks_by_monitoring_and_organization', args=[monitoring.pk, organization.pk]), request.GET.urlencode())
        title = _('Add new task for %s') % organization.name
    else:
        organization = None
        redirect = '%s?%s' % (reverse('exmo.exmo2010.view.task.tasks_by_monitoring', args=[monitoring.pk]), request.GET.urlencode())
        title = _('Add new task for %s') % monitoring
    redirect = redirect.replace("%","%%")
    if request.user.is_superuser:
        if request.method == 'GET':
            form = TaskForm()
            group, created = Group.objects.get_or_create(name = 'experts')
            form.fields['user'].queryset = User.objects.filter(is_active = True).filter(Q(groups = group) | Q(is_superuser = True))
            if not organization:
                form.fields['organization'].queryset = Organization.objects.filter(type=monitoring.type)
            return render_to_response(
                'exmo2010/task_form.html',
                {
                    'monitoring': monitoring,
                    'organization': organization,
                    'title': title,
                    'form': form
                },
                context_instance=RequestContext(request),
            )
        if request.method == 'POST':
            form = TaskForm(request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(redirect)
            else:
              return render_to_response(
                'exmo2010/task_form.html',
                {
                    'monitoring': monitoring,
                    'organization': organization,
                    'title': title,
                    'form': form
                },
                context_instance=RequestContext(request),
            )
    else: return HttpResponseForbidden(_('Forbidden'))



@revision.create_on_success
@login_required
def task_manager(request, id, method, monitoring_id=None, organization_id=None):
    task = get_object_or_404(Task, pk = id)
    monitoring = task.monitoring
    organization = task.organization
    organization_from_get = request.GET.get('organization','')
    if organization_id or organization_from_get:
        redirect = '%s?%s' % (reverse('exmo.exmo2010.view.task.tasks_by_monitoring_and_organization', args=[monitoring.pk, organization.pk]), request.GET.urlencode())
    else:
        redirect = '%s?%s' % (reverse('exmo.exmo2010.view.task.tasks_by_monitoring', args=[monitoring.pk]), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    if method == 'delete':
      title = _('Delete task %s') % task
      if request.user.is_superuser:
        return delete_object(request, model = Task, object_id = id, post_delete_redirect = redirect, extra_context = {'monitoring': monitoring, 'organization': organization, 'title': title })
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'close':
      title = _('Close task %s') % task
      if request.user.has_perm('exmo2010.close_task', task):
        if task.open:
          if request.method == 'GET':
            return render_to_response(
                'exmo2010/task_confirm_close.html',
                {
                    'object': task,
                    'monitoring': monitoring,
                    'organization': organization,
                    'title': title,
                },
                context_instance=RequestContext(request),
                )
          elif request.method == 'POST':
            try:
                task.ready = True
            except ValidationError, e:
                return HttpResponseForbidden('%s' % e.message_dict.get('__all__')[0])
            return HttpResponseRedirect(redirect)
        else:
          return HttpResponseForbidden(_('Already closed'))
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'approve':
      title = _('Approve task for %s') % task
      if request.user.is_superuser:
        if not task.approved:
          if request.method == 'GET':
            return render_to_response(
                'exmo2010/task_confirm_approve.html',
                {
                    'object': task,
                    'monitoring': monitoring,
                    'organization': organization,
                    'title': title
                },
                context_instance=RequestContext(request),
                )
          elif request.method == 'POST':
            try:
                task.approved = True
            except ValidationError, e:
                return HttpResponseForbidden('%s' % e.message_dict.get('__all__')[0])
            return HttpResponseRedirect(redirect)
        else: return HttpResponseForbidden(_('Already approved'))
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'open':
      title = _('Open task %s') % task
      if request.user.is_superuser:
        if task.approved:
          if request.method == 'GET':
            return render_to_response(
                'exmo2010/task_confirm_open.html',
                {
                    'object': task,
                    'monitoring': monitoring,
                    'organization': organization,
                    'title': title
                },
                context_instance=RequestContext(request),
                )
          elif request.method == 'POST':
            try:
                task.open = True
            except ValidationError, e:
                return HttpResponseForbidden('%s' % e.message_dict.get('__all__')[0])
            return HttpResponseRedirect(redirect)
        else: return HttpResponseForbidden(_('Already open'))
      else: return HttpResponseForbidden(_('Forbidden'))
    else: #update
      title = _('Edit task %s') % task
      if request.user.is_superuser:
        return update_object(request, form_class = TaskForm, object_id = id, post_save_redirect = redirect, extra_context = {'monitoring': monitoring, 'organization': organization, 'title': title })
      else: return HttpResponseForbidden(_('Forbidden'))



def tasks_by_monitoring(request, id):
    monitoring = get_object_or_404(Monitoring, pk = id)
    profile = None
    if request.user.is_active: profile = request.user.get_profile()
    if not request.user.has_perm('exmo2010.view_monitoring', monitoring): return HttpResponseForbidden(_('Forbidden'))
    title = _('Task list for %s') % monitoring
    task_list = []
    queryset = Task.objects.filter(monitoring = monitoring)
    for task in queryset:
        if request.user.has_perm('exmo2010.view_task', task): task_list.append(task.pk)
    if not task_list and not request.user.is_superuser: return HttpResponseForbidden(_('Forbidden'))
    queryset = Task.objects.filter(pk__in = task_list)
    queryset = queryset.extra(select = {'complete': Task._complete})
    if request.user.is_superuser:
        headers = (
                (_('Organization'), 'organization__name', 'organization__name', None, None),
                (_('Expert'), 'user__username', 'user__username', None, None),
                (_('Status'), 'status', 'status', int, Task.TASK_STATUS),
                (_('Complete, %'), 'complete', None, None, None),
              )
    elif profile and profile.is_expert:
        headers = (
                (_('Organization'), 'organization__name', 'organization__name', None, None),
                (_('Status'), 'status', 'status', int, Task.TASK_STATUS),
                (_('Complete, %'), 'complete', None, None, None),
              )
    else:
        headers = (
                (_('Organization'), 'organization__name', 'organization__name', None, None),
                (_('Complete, %'), 'complete', None, None, None),
              )

    return table(
        request,
        headers,
        queryset = queryset,
        paginate_by = 50,
        extra_context = {
            'monitoring': monitoring,
            'title': title,
            },
        template_name = "exmo2010/task_list.html",
        )



@login_required
def task_mass_assign_tasks(request, id):
  if not request.user.is_superuser:
    return HttpResponseForbidden(_('Forbidden'))
  monitoring = get_object_or_404(Monitoring, pk = id)
  organizations = Organization.objects.filter(type = monitoring.type)
  group, created = Group.objects.get_or_create(name = 'experts')
  users = User.objects.filter(is_active = True).filter(Q(groups = group) | Q(is_superuser = True))
  log = []
  if request.method == 'POST' and request.POST.has_key('organizations') and request.POST.has_key('users'):
    for organization_id in request.POST.getlist('organizations'):
      for user_id in request.POST.getlist('users'):
        try:
          user = User.objects.get(pk = (user_id))
          organization = Organization.objects.get(pk = int(organization_id))
          task = Task(
            user = user,
            organization = organization,
            monitoring = monitoring,
            status = Task.TASK_OPEN,
          )
          task.full_clean()
          task.save()
        except ValidationError, e:
          log.append('; '.join(['%s: %s' % (i[0], ', '.join(i[1])) for i in e.message_dict.items()]))
        except Exception, e:
          log.append(e)
        else:
          log.append('%s: %s' % (user.username, organization.name))
  return render_to_response(
    'exmo2010/mass_assign_tasks.html', {
        'organizations': organizations,
        'users': users,
        'monitoring': monitoring,
        'log': log,
        'title':_('Mass assign tasks'),
    }, context_instance=RequestContext(request))
