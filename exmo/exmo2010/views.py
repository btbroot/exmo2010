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
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import update_object, create_object, delete_object
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from exmo.exmo2010.models import Organization, Parameter, Score, Task, Category, Subcategory

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
    if not task.open and not request.user.is_superuser:
	return HttpResponseForbidden('Task closed')
    return create_object(
      request,
      form_class = ScoreForm,
      post_save_redirect = redirect,
      extra_context = {
        'create': True,
        'task': task,
        'parameter': parameter,
        }
    )

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
      if request.user.is_superuser or request.user == score.task.user:
	return delete_object(request, model = Score, object_id = score.pk, post_delete_redirect = redirect)
      else: return HttpResponseForbidden_(('Forbidden'))
    else: #update
      if not score.task.open and not request.user.is_superuser:
	return HttpResponseForbidden(_('Task closed'))
      if request.user.is_superuser or request.user == score.task.user:
        if request.method == 'POST':
	    form = ScoreForm(request.POST,instance=score)
	    message = construct_change_message(request,form, None)
	    revision.comment = message
      else: return HttpResponseForbidden(_('Forbidden'))
      return update_object(
	request,
	form_class = ScoreForm,
	object_id = score.pk,
	post_save_redirect = redirect,
	extra_context = {
          'task': score.task,
          'parameter': score.parameter,
        }
      )

from django.db.models import Q
@login_required
def score_list_by_task(request, task_id):
    task = get_object_or_404(Task, pk = task_id)
    if not task.open and not request.user.is_superuser:
	return HttpResponseForbidden('Task closed')
    if request.user.is_superuser or request.user == task.user:
      queryset = Parameter.objects.filter(Q(organizationType=task.organization.type), ~Q(exclude=task.organization)).extra(
        select={
          'status':'SELECT id FROM %s WHERE task_id = %s and parameter_id = %s.id' % (Score._meta.db_table,task.pk, Parameter._meta.db_table),
        }
      )
    else: return HttpResponseForbidden('Forbidden')
    return table(request,
      headers=(
        ('Code', None, None, None),
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
      extra_context={'task': task, 'categories': Category.objects.all(), 'subcategories': Subcategory.objects.all()},
    )


import csv
from django.http import HttpResponse
@login_required
def task_export(request, id):
    task = get_object_or_404(Task, pk = id)
    if not task.open and not request.user.is_superuser:
	return HttpResponseForbidden('Task closed')
    if not request.user.is_superuser and request.user != task.user:
        return HttpResponseForbidden('Forbidden')
    parameters = Parameter.objects.filter(organizationType=task.organization.type).exclude(exclude=task.organization)
    scores     = Score.objects.filter(task=id)
    response = HttpResponse(mimetype='text/csv')
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
    for p in parameters:
        out = (
            p.fullcode(),
            p.name.encode("utf-8"),
            p.type.name.encode("utf-8")
        )
        try:
            s = scores.get(parameter=p)
        except:
            pass
        else:
            out += (
                s.found,
                s.complete,
                s.completeComment.encode("utf-8"),
                s.topical,
                s.topicalComment.encode("utf-8"),
                s.accessible,
                s.accessibleComment.encode("utf-8"),
                s.hypertext,
                s.hypertextComment.encode("utf-8"),
                s.document,
                s.documentComment.encode("utf-8"),
                s.image,
                s.imageComment.encode("utf-8"),
                s.comment.encode("utf-8")
            )
        writer.writerow(out)
    return response

import re
@revision.create_on_success
@login_required
def task_import(request, id):
    task = get_object_or_404(Task, pk = id)
    if not task.open and not request.user.is_superuser:
        return HttpResponseForbidden('Task closed')
    if request.user != task.user and not request.user.is_superuser:
        return HttpResponseForbidden('Forbidden')
    if not request.FILES.has_key('taskfile'):
        return HttpResponseRedirect(reverse('exmo.exmo2010.views.score_list_by_task', args=[id]))
    reader = csv.reader(request.FILES['taskfile'])
    errLog = []
    rowCount = 0
    try:
        for row in reader:
            code = re.match('^(\d+)\.(\d+)\.(\d+)$', row[0])
            if not code: continue
            parameter = Parameter.objects.filter(group__group__code=code.group(1)).filter(group__code=code.group(2)).get(code=code.group(3))
            try:
                score = Score.objects.get(task = task, parameter = parameter)
            except Score.DoesNotExist:
                score = Score()
            try:
                score.task              = task
                score.parameter         = parameter
                score.found             = int(row[3] or 0)
                score.complete          = int(row[4] or 0)
                score.completeComment   = row[5]
                score.topical           = int(row[6] or 0)
                score.topicalComment    = row[7]
                score.accessible        = int(row[8] or 0)
                score.accessibleComment = row[9]
                score.hypertext         = int(row[10] or 0)
                score.hypertextComment  = row[11]
                score.document          = int(row[12] or 0)
                score.documentComment   = row[13]
                score.image             = int(row[14] or 0)
                score.imageComment      = row[15]
                score.comment           = row[16]
                from django.core.exceptions import ValidationError
                try:
                    score.full_clean()
                    score.save()
                except ValidationError, e:
                    errLog.append("%d: %s" % (reader.line_num, ' '.join(s for s in e.message_dict['__all__'])))
            except Exception, e :
                errLog.append("%d: %s" % (reader.line_num, e))
            else:
                rowCount += 1
    except csv.Error, e:
           errLog.append("%d: %s" % (reader.line_num, e))
    return render_to_response('exmo2010/task_import_log.html',
        { 'task': id, 'file': request.FILES['taskfile'], 'errLog': errLog, 'rowCount': rowCount }
    )


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


@login_required
def tasks(request):
    queryset = Task.objects.extra(select = {'complete': Task.c_complete})
    # Or, filtered by user
    if request.user.is_superuser:
      headers = (
                ('', None, None, None),
                (_('Organization'), 'organization__name', 'organization__name', None),
                (_('Expert'), 'user__username', 'user__username', None),
                (_('Open'), 'open', 'open', int),
                (_('Complete%'), 'complete', None, None)
              )
    else:
      queryset = queryset.filter(user = request.user)
    # Or, without Expert
      headers = (
                (_('Organization'), 'organization__name', 'organization__name', None),
                (_('Open'), 'open', 'open', int),
                (_('Complete%'), 'complete', None, None)
              )
    return table(request, headers, queryset = queryset, paginate_by = 15)


from django.http import HttpResponseRedirect
from django.template import RequestContext
@revision.create_on_success
@login_required
def task_manager(request, id, method):
    redirect = '%s?%s' % (reverse('exmo.exmo2010.views.tasks'), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    if method == 'add':
      if request.user.is_superuser:
	return create_object(request, form_class = TaskForm, post_save_redirect = redirect)
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'delete':
      task = get_object_or_404(Task, pk = id)
      if request.user.is_superuser:
	return delete_object(request, model = Task, object_id = id, post_delete_redirect = redirect)
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'close':
      task = get_object_or_404(Task, pk = id)
      if request.user.is_superuser or task.user == request.user:
        if task.open:
          if request.method == 'GET':
	    return render_to_response('exmo2010/task_confirm_close.html', { 'object': task }, context_instance=RequestContext(request))
          elif request.method == 'POST':
	    task.open = False
	    task.save()
	    return HttpResponseRedirect(redirect)
	else: return HttpResponseForbidden(_('Already closed'))
      else: return HttpResponseForbidden(_('Forbidden'))
    else: #update
      task = get_object_or_404(Task, pk = id)
      if request.user.is_superuser or request.user == task.user:
        return update_object(request, form_class = TaskForm, object_id = id, post_save_redirect = redirect)
      else: return HttpResponseForbidden(_('Forbidden'))
