# This file is part of EXMO2010 software.
# Copyright 2010 Al Nikolov
# Copyright 2010 Institute for Information Freedom Development
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
from exmo.exmo2010.sort_headers import SortHeaders
from exmo.exmo2010.forms import ScoreForm, TaskForm
from exmo.exmo2010.forms import FeedbackForm
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import update_object, create_object, delete_object
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from exmo.exmo2010.models import Organization, Parameter, Score, Task, Category, Subcategory
from exmo.exmo2010.models import Feedback
from exmo.exmo2010.models import Monitoring
from django.contrib.auth.models import Group
from django.db.models import Q
from exmo.exmo2010.helpers import PERM_NOPERM, PERM_ADMIN, PERM_EXPERT, PERM_ORGANIZATION, PERM_CUSTOMER
from exmo.exmo2010.helpers import check_permission

@login_required
def parameter_by_organization_list(request, organization_id):
  organization = get_object_or_404(Organization, pk = organization_id)
  return object_list(
    request,
    queryset = Parameter.objects.filter(
      organizationType = organization.type,
    ),
    template_name = 'exmo2010/parameter_by_organization_list.html',
    extra_context = {'organization': organization},
  )

def score_by_organization_parameter_detail(request, organization_id, parameter_id):
  organization = get_object_or_404(Organization, pk = organization_id)
  parameter = get_object_or_404(Parameter, pk = parameter_id, organizationType = organization.type)
  score, created = Score.objects.get_or_create(
    organization = organization,
    parameter = parameter,
    defaults = {'user': request.user }
  )
  #if request.method == 'POST':
    #form = ContactForm(request.POST) # A form bound to the POST data
      #if form.is_valid(): # All validation rules pass
          ## Process the data in form.cleaned_data
          ## ...
          #return HttpResponseRedirect('/thanks/') # Redirect after POST
  #else:
      #form = ContactForm() # An unbound form
  return update_object(request, model = Score, object_id = score.pk)


@login_required
def score_detail(request, task_id, parameter_id):
    task = get_object_or_404(Task, pk = task_id)
    parameter = get_object_or_404(Parameter, pk = parameter_id)
    redirect = "%s?%s#parameter_%s" % (reverse('exmo.exmo2010.views.score_list_by_task', args=[task.pk]), request.GET.urlencode(), parameter.group.fullcode())
    redirect = redirect.replace("%","%%")
    title = _('New score for %(name)s from %(user)s') %  { 'name': task.organization.name, 'user': request.user }
    if check_permission(request.user, task) == PERM_ADMIN or (check_permission(request.user, task) == PERM_EXPERT and task.open):
      return create_object(
        request,
        form_class = ScoreForm,
        post_save_redirect = redirect,
        extra_context = {
          'task': task,
          'parameter': parameter,
          'title': title,
          }
      )
    elif check_permission(request.user, task) == PERM_EXPERT and not task.open:
      return HttpResponseForbidden(_('Task closed'))
    else:
      return HttpResponseForbidden(_('Forbidden'))


from django.http import HttpResponseForbidden
from django.core.urlresolvers import reverse
from reversion import revision
from exmo.exmo2010.helpers import construct_change_message
@revision.create_on_success
@login_required
def score_detail_direct(request, score_id, method='update'):
    score = get_object_or_404(Score, pk = score_id)
    redirect = "%s?%s#parameter_%s" % (reverse('exmo.exmo2010.views.score_list_by_task', args=[score.task.pk]), request.GET.urlencode(), score.parameter.group.fullcode())
    redirect = redirect.replace("%","%%")
    if method == 'delete':
      title = _('Delete score %s') % score.parameter
      if check_permission(request.user, score.task) == PERM_ADMIN or (check_permission(request.user, score.task) == PERM_EXPERT and score.task.open):
        return delete_object(request, model = Score, object_id = score.pk, post_delete_redirect = redirect, extra_context = {'title': title})
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'update':
      title = _('Edit score %s') % score.parameter
      if check_permission(request.user, score.task) == PERM_EXPERT and not score.task.open:
        return HttpResponseForbidden(_('Task closed'))
      elif check_permission(request.user, score.task) == PERM_ADMIN or (check_permission(request.user, score.task) == PERM_EXPERT and score.task.open):
        if request.method == 'POST':
            form = ScoreForm(request.POST,instance=score)
            message = construct_change_message(request,form, None)
            revision.comment = message
      else:
        return HttpResponseForbidden(_('Forbidden'))
      return update_object(
	request,
	form_class = ScoreForm,
	object_id = score.pk,
	post_save_redirect = redirect,
	extra_context = {
          'task': score.task,
          'parameter': score.parameter,
          'comments': Feedback.objects.filter(score = score),
          'title': title,
        }
      )
    elif method == 'view':
      title = _('View score %s') % score.parameter
      return object_detail(
	request,
	queryset = Score.objects.all(),
	object_id = score.pk,
	extra_context = {
          'task': score.task,
          'parameter': score.parameter,
          'comments': Feedback.objects.filter(score = score),
          'title': title,
        }
      )
    else: return HttpResponseForbidden(_('Forbidden'))


@login_required
def score_list_by_task(request, task_id, report=None):
    task = get_object_or_404(Task, pk = task_id)
    task = Task.objects.extra(select = {'complete': Task._complete, 'openness': Task._openness}).get(pk = task_id)
    title = _('Score list for %s') % ( task.organization.name )
    if check_permission(request.user, task) != PERM_NOPERM:
      queryset = Parameter.objects.filter(monitoring = task.monitoring).exclude(exclude = task.organization).extra(
        select={
          'status':'SELECT id FROM %s WHERE task_id = %s and parameter_id = %s.id' % (Score._meta.db_table, task.pk, Parameter._meta.db_table),
        }
      )
    else: return HttpResponseForbidden(_('Forbidden'))
    if report:
      # Print report
      return object_list(
        request,
        queryset = queryset,
        template_name='exmo2010/task_report.html',
        extra_context={
          'task': task,
          'categories': Category.objects.all(),
          'subcategories': Subcategory.objects.all(),
          'title': title,
          'report': report
        }
      )
    else:
      # Regular application page
      return table(
        request,
        headers=(
          (_('Code'), None, None, None),
          (_('Name'), 'name', 'name', None),
          (_('Found'), None, None, None),
          (_('Complete'), None, None, None),
          (_('Topical'), None, None, None),
          (_('Accessible'), None, None, None),
          (_('HTML'), None, None, None),
          (_('Document'), None, None, None),
          (_('Image'), None, None, None),
          (_('Action'), None, None, None),
        ),
        queryset=queryset,
        template_name='exmo2010/score_list.html',
        extra_context={
          'task': task,
          'categories': Category.objects.all(),
          'subcategories': Subcategory.objects.all(),
          'title': title,
          }
      )


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
    if check_permission(request.user, task) == PERM_NOPERM:
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
            out += (
                s.found,
                s.complete,
                safeConvert(s.completeComment),
                s.topical,
                safeConvert(s.topicalComment),
                s.accessible,
                safeConvert(s.accessibleComment),
                s.hypertext,
                safeConvert(s.hypertextComment),
                s.document,
                safeConvert(s.documentComment),
                s.image,
                safeConvert(s.imageComment),
                safeConvert(s.comment)
            )
        writer.writerow(out)
    return response

import re
from django.core.exceptions import ValidationError
@revision.create_on_success
@login_required
def task_import(request, id):

    def safeConvert(string, toType):
        if string:
            return toType(string)
        else:
            return None

    task = get_object_or_404(Task, pk = id)
    if check_permission(request.user, task) == PERM_EXPERT and not task.open:
        return HttpResponseForbidden(_('Task closed'))
    elif check_permission(request.user, task) != PERM_ADMIN and not (check_permission(request.user, task) == PERM_EXPERT and task.open):
        return HttpResponseForbidden(_('Forbidden'))
    if not request.FILES.has_key('taskfile'):
        return HttpResponseRedirect(reverse('exmo.exmo2010.views.score_list_by_task', args=[id]))
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


def table(request, headers, **kwargs):
  '''Generic sortable table view'''
  sort_headers = SortHeaders(request, headers)
  if sort_headers.get_order_by():
        kwargs['queryset'] = kwargs['queryset'].order_by(
        sort_headers.get_order_by())
  kwargs['queryset'] = kwargs['queryset'].filter(
    **sort_headers.get_filter()
  )
  if 'extra_context' not in kwargs:
    kwargs['extra_context'] = {}
  kwargs['extra_context'].update(
    {
      'headers': sort_headers.headers(),
    }
  )
  return object_list(request, **kwargs)


def tasks(request):
    return HttpResponseRedirect(reverse('exmo.exmo2010.views.monitoring_list'))

@login_required
def tasks_by_monitoring_and_organization(request, monitoring_id, organization_id):
    '''We have 3 generic group: experts, customers, organizations.
    Superusers: all tasks
    Experts: only own tasks
    Customers: all approved tasks
    organizations: all approved tasks of organizations that belongs to user
    Also for every ogranization we can have group'''
    monitoring = get_object_or_404(Monitoring, pk = monitoring_id)
    organization = get_object_or_404(Organization, pk = organization_id, type = monitoring.type)
    title = _('Task list for %s') % organization.name
    queryset = Task.objects.extra(select = {'complete': Task._complete, 'openness': Task._openness})
    queryset = queryset.filter(monitoring = monitoring, organization = organization)
    groups = request.user.groups.all()
    # Or, filtered by user
    if request.user.is_superuser:
      headers = (
                (_('Organization'), 'organization__name', 'organization__name', None),
                (_('Expert'), 'user__username', 'user__username', None),
                (_('Status'), 'status', 'status', int),
                (_('Complete, %'), 'complete', None, None),
                (_('Openness, %'), 'openness', None, None)
              )
    elif Group.objects.get(name='experts') in groups:
      queryset = queryset.filter(user = request.user)
    # Or, without Expert
      headers = (
                (_('Organization'), 'organization__name', 'organization__name', None),
                (_('Status'), 'status', 'status', int),
                (_('Complete, %'), 'complete', None, None),
                (_('Openness, %'), 'openness', None, None)
              )
    elif Group.objects.get(name='customers') in groups:
      queryset = Task.approved_tasks.all()
      queryset = queryset.extra(select = {'complete': Task._complete, 'openness': Task._openness})
      queryset = queryset.filter(monitoring = monitoring, organization = organization)
      headers = (
                (_('Organization'), 'organization__name', 'organization__name', None),
                (_('Complete, %'), 'complete', None, None),
                (_('Openness, %'), 'openness', None, None)
              )
    elif Group.objects.get(name='organizations') in groups:
      orgs = []
      for group in groups:
        org = None
        try: org = Organization.objects.get(keyname = group.name)
        except: continue
        if org: orgs.append(org)
      query = " | ".join(["Q(organization__pk = %d)" % org.pk for org in orgs])
      if query:
        queryset = Task.approved_tasks.all()
        queryset = queryset.extra(select = {'complete': Task._complete, 'openness': Task._openness})
        queryset = queryset.filter(monitoring = monitoring, organization = organization)
        queryset = queryset.filter(eval(query))
        headers = (
                (_('Organization'), 'organization__name', 'organization__name', None),
                (_('Complete, %'), 'complete', None, None),
                (_('Openness, %'), 'openness', None, None)
                )
      else: #no organization to show
        return HttpResponseForbidden(_('Forbidden'))
    else: #we dont know how are you
        return HttpResponseForbidden(_('Forbidden'))
    return table(request, headers, queryset = queryset, paginate_by = 15, extra_context = {'monitoring': monitoring, 'organization': organization, 'title': title })



from django.http import HttpResponseRedirect
from django.template import RequestContext
@revision.create_on_success
@login_required
def task_manager(request, monitoring_id, organization_id, id, method):
    monitoring = get_object_or_404(Monitoring, pk = monitoring_id)
    organization = get_object_or_404(Organization, pk = organization_id, type = monitoring.type)
    redirect = '%s?%s' % (reverse('exmo.exmo2010.views.tasks_by_monitoring_and_organization', args=[monitoring.pk, organization.pk]), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    if method == 'add':
      title = _('Add new task for %s') % organization.name
      if request.user.is_superuser:
	return create_object(request, form_class = TaskForm, post_save_redirect = redirect, extra_context = {'monitoring': monitoring, 'organization': organization, 'title': title })
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'delete':
      task = get_object_or_404(Task, pk = id)
      title = _('Delete task %s') % task
      if request.user.is_superuser:
	return delete_object(request, model = Task, object_id = id, post_delete_redirect = redirect, extra_context = {'monitoring': monitoring, 'organization': organization, 'title': title })
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'close':
      task = get_object_or_404(Task, pk = id)
      title = _('Close task %s') % task
      if request.user.is_superuser or check_permission(request.user, task) == PERM_EXPERT:
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
	    task.ready = True
	    task.save()
	    return HttpResponseRedirect(redirect)
	else:
	  return HttpResponseForbidden(_('Already closed'))
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'approve':
      task = get_object_or_404(Task, pk = id)
      title = _('Approve task for %s') % task
      if request.user.is_superuser:
        if task.ready:
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
	    task.approved= True
	    task.save()
	    return HttpResponseRedirect(redirect)
	else: return HttpResponseForbidden(_('Already approved'))
      else: return HttpResponseForbidden(_('Forbidden'))
    else: #update
      task = get_object_or_404(Task, pk = id)
      title = _('Edit task %s') % task
      if request.user.is_superuser or check_permission(request.user, task) == PERM_EXPERT:
        return update_object(request, form_class = TaskForm, object_id = id, post_save_redirect = redirect, extra_context = {'monitoring': monitoring, 'organization': organization, 'title': title })
      else: return HttpResponseForbidden(_('Forbidden'))



@login_required
def add_comment(request, score_id):
    score = get_object_or_404(Score, pk = score_id)
    if check_permission(request.user, score.task) != PERM_NOPERM:
        if request.user.is_superuser or check_permission(request.user, score.task) == PERM_EXPERT:
            method = 'update'
        else:
            method = 'view'
        return create_object(
            request,
            form_class = FeedbackForm,
            post_save_redirect = reverse('exmo.exmo2010.views.score_detail_direct', args = [score.pk, method]),
            extra_context = {
                'score': score,
                'title': _('Add new comment'),
            }
        )
    else: return HttpResponseForbidden(_('Forbidden'))



@login_required
def monitoring_list(request):
    queryset = Monitoring.objects.all()
    headers =   (
                (_('Name'), 'name', 'name', None),
                (_('Type'), 'type__name', 'type__name', None),
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
    redirect = '%s?%s' % (reverse('exmo.exmo2010.views.monitoring_list'), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    if method == 'add':
        title = _('Add new monitoring')
        return create_object(request, model = Monitoring, post_save_redirect = redirect, extra_context = {'title': title})
    elif method == 'delete':
        monitoring = get_object_or_404(Monitoring, pk = id)
        title = _('Delete monitoring %s') % monitoring.type
        return delete_object(
            request,
            model = Monitoring,
            object_id = id,
            post_delete_redirect = redirect,
            extra_context = {
                'title': title,
                'deleted_objects': Task.objects.filter(monitoring = monitoring),
                }
            )
    else: #update
        monitoring = get_object_or_404(Monitoring, pk = id)
        title = _('Edit monitoring %s') % monitoring.type
        return update_object(request, model = Monitoring, object_id = id, post_save_redirect = redirect, extra_context = {'title': title})



@login_required
def organization_list(request, id):
    monitoring = get_object_or_404(Monitoring, pk = id)
    title = _('Organizations for monitoring %(name)s with type %(type)s') % {'name': monitoring.name, 'type': monitoring.type}
    queryset = Organization.objects.filter(type = monitoring.type)
    groups = request.user.groups.all()
    if Group.objects.get(name='organizations') in groups:
      orgs = []
      for group in groups:
        org = None
        try: org = Organization.objects.get(keyname = group.name)
        except: continue
        if org: orgs.append(org)
      query = " | ".join(["Q(pk = %d)" % org.pk for org in orgs])
      if query:
        queryset = queryset.filter(eval(query))
    headers =   (
                (_('Name'), 'name', 'name', None),
                )
    return table(
        request,
        headers,
        queryset = queryset,
        paginate_by = 50,
        extra_context = {
            'title': title,
            'monitoring': monitoring,
        },
    )



@login_required
def organization_manager(request, monitoring_id, id, method):
    if not request.user.is_superuser:
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = get_object_or_404(Monitoring, pk = monitoring_id)
    redirect = '%s?%s' % (reverse('exmo.exmo2010.views.organization_list', args=[monitoring.pk]), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    if method == 'add':
        title = _('Add new organization for %s') % monitoring.type
        return create_object(request, model = Organization, post_save_redirect = redirect, extra_context = {'title': title, 'monitoring': monitoring,})
    elif method == 'delete':
        organization = get_object_or_404(Organization, pk = id)
        title = _('Delete organization %s') % monitoring.type
        return delete_object(
            request,
            model = Organization,
            object_id = id,
            post_delete_redirect = redirect,
            extra_context = {
                'title': title,
                'monitoring': monitoring,
                'deleted_objects': Task.objects.filter(organization = organization),
                }
            )
    else: #update
        organization = get_object_or_404(Organization, pk = id)
        title = _('Edit organization %s') % monitoring.type
        return update_object(request, model = Organization, object_id = id, post_save_redirect = redirect, extra_context = {'title': title, 'monitoring': monitoring,})



@login_required
def parameter_manager(request, task_id, id, method):
    if not request.user.is_superuser:
        return HttpResponseForbidden(_('Forbidden'))
    task = get_object_or_404(Task, pk = task_id)
    parameter = get_object_or_404(Parameter, pk = id)
    redirect = '%s?%s' % (reverse('exmo.exmo2010.views.score_list_by_task', args=[task.pk]), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    if method == 'delete':
        title = _('Delete parameter %s') % parameter
        return delete_object(
            request,
            model = Parameter,
            object_id = id,
            post_delete_redirect = redirect,
            extra_context = {
                'title': title,
                'task': task,
                }
            )
    else: #update
        title = _('Edit parameter %s') % parameter
        return update_object(
            request,
            model = Parameter,
            object_id = id,
            post_save_redirect = redirect,
            extra_context = {
                'title': title,
                'task': task,
                }
            )



@login_required
def rating(request, id):
  monitoring = get_object_or_404(Monitoring, pk = id)
  return object_list(
    request,
    queryset = Organization.objects.filter(type = monitoring.type).filter(task__status = Task.TASK_OPEN).extra(select = {'openness': Task._openness}).order_by('-openness'),
    template_name = 'exmo2010/rating.html',
    extra_context = { 'monitoring': monitoring }
  )



