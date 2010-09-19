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
from exmo.exmo2010.models import TASK_APPROVED, TASK_OPEN, TASK_READY
from exmo.exmo2010.models import Feedback
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
    if check_permission(request.user, task) == PERM_ADMIN or (check_permission(request.user, task) == PERM_EXPERT and task.status == TASK_OPEN):
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
    elif check_permission(request.user, task) == PERM_EXPERT and task.status != TASK_OPEN:
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
      if check_permission(request.user, score.task) == PERM_ADMIN or (check_permission(request.user, score.task) == PERM_EXPERT and score.task.status == TASK_OPEN):
        return delete_object(request, model = Score, object_id = score.pk, post_delete_redirect = redirect)
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'update':
      if check_permission(request.user, score.task) == PERM_EXPERT and score.task.status != TASK_OPEN:
        return HttpResponseForbidden(_('Task closed'))
      elif check_permission(request.user, score.task) == PERM_ADMIN or (check_permission(request.user, score.task) == PERM_EXPERT and score.task.status == TASK_OPEN):
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
          'comments': Feedback.objects.filter(score = score)
        }
      )
    elif method == 'view':
      return object_detail(
	request,
	queryset = Score.objects.all(),
	object_id = score.pk,
	extra_context = {
          'task': score.task,
          'parameter': score.parameter,
          'comments': Feedback.objects.filter(score = score)
        }
      )
    else: return HttpResponseForbidden(_('Forbidden'))


@login_required
def score_list_by_task(request, task_id):
    task = get_object_or_404(Task, pk = task_id)
    if check_permission(request.user, task) != PERM_NOPERM:
      queryset = Parameter.objects.filter(monitoring = task.monitoring).exclude(exclude = task.organization).extra(
        select={
          'status':'SELECT id FROM %s WHERE task_id = %s and parameter_id = %s.id' % (Score._meta.db_table, task.pk, Parameter._meta.db_table),
        }
      )
    else: return HttpResponseForbidden(_('Forbidden'))
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
    if check_permission(request.user, task) == PERM_NOPERM:
        return HttpResponseForbidden(_('Forbidden'))
    parameters = Parameter.objects.filter(organizationType = task.organization.type).exclude(exclude = task.organization)
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
    for p in parameters:
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
    if check_permission(request.user, task) == PERM_EXPERT and task.status != TASK_OPEN:
        return HttpResponseForbidden(_('Task closed'))
    elif check_permission(request.user, task) != PERM_ADMIN and not (check_permission(request.user, task) == PERM_EXPERT and task.status == TASK_OPEN):
        return HttpResponseForbidden(_('Forbidden'))
    if not request.FILES.has_key('taskfile'):
        return HttpResponseRedirect(reverse('exmo.exmo2010.views.score_list_by_task', args=[id]))
    reader = csv.reader(request.FILES['taskfile'])
    errLog = []
    rowCount = 0
    try:
        for row in reader:
            try:
                code = re.match('^(\d+)\.(\d+)\.(\d+)$', row[0])
                if not code or (
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
                rowCount += 1
    except csv.Error, e:
           errLog.append("row %d (csv). %s" % (reader.line_num, e))
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
    '''We have 3 generic group: experts, customers, organizations.
    Superusers: all tasks
    Experts: only own tasks
    Customers: all approved tasks
    organizations: all approved tasks of organizations that belongs to user
    Also for every ogranization we can have group'''

    queryset = Task.objects.extra(select = {'complete': Task.c_complete})
    groups = request.user.groups.all()
    # Or, filtered by user
    if request.user.is_superuser:
      headers = (
                ('', None, None, None),
                (_('Organization'), 'organization__name', 'organization__name', None),
                (_('Expert'), 'user__username', 'user__username', None),
                (_('Status'), 'status', 'status', int),
                (_('Complete%'), 'complete', None, None)
              )
    elif Group.objects.get(name='experts') in groups:
      queryset = queryset.filter(user = request.user)
    # Or, without Expert
      headers = (
                (_('Organization'), 'organization__name', 'organization__name', None),
                (_('Status'), 'status', 'status', int),
                (_('Complete%'), 'complete', None, None)
              )
    elif Group.objects.get(name='customers') in groups:
      queryset = queryset.filter(status = TASK_APPROVED)
      headers = (
                (_('Organization'), 'organization__name', 'organization__name', None),
                (_('Complete%'), 'complete', None, None)
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
        queryset = queryset.filter(status = TASK_APPROVED)
        queryset = queryset.filter(eval(query))
        headers = (
                (_('Organization'), 'organization__name', 'organization__name', None),
                (_('Complete%'), 'complete', None, None)
                )
      else: #no organization to show
        return HttpResponseForbidden(_('Forbidden'))
    else: #we dont know how are you
        return HttpResponseForbidden(_('Forbidden'))
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
      if request.user.is_superuser or check_permission(request.user, task) == PERM_EXPERT:
        if task.status == TASK_OPEN:
          if request.method == 'GET':
	    return render_to_response('exmo2010/task_confirm_close.html', { 'object': task }, context_instance=RequestContext(request))
          elif request.method == 'POST':
	    task.status = TASK_READY
	    task.save()
	    return HttpResponseRedirect(redirect)
	else:
	  return HttpResponseForbidden(_('Already closed'))
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'approve':
      task = get_object_or_404(Task, pk = id)
      if request.user.is_superuser:
        if task.status == TASK_READY:
          if request.method == 'GET':
	    return render_to_response('exmo2010/task_confirm_approve.html', { 'object': task }, context_instance=RequestContext(request))
          elif request.method == 'POST':
	    task.status = TASK_APPROVED
	    task.save()
	    return HttpResponseRedirect(redirect)
	else: return HttpResponseForbidden(_('Already approved'))
      else: return HttpResponseForbidden(_('Forbidden'))
    else: #update
      task = get_object_or_404(Task, pk = id)
      if request.user.is_superuser or check_permission(request.user, task) == PERM_EXPERT:
        return update_object(request, form_class = TaskForm, object_id = id, post_save_redirect = redirect)
      else: return HttpResponseForbidden(_('Forbidden'))


@login_required
def add_comment(request, score_id):
    score = get_object_or_404(Score, pk = score_id)
    if check_permission(request.user, score.task) != PERM_NOPERM:
        return create_object(
            request,
            form_class = FeedbackForm,
            post_save_redirect = reverse('exmo.exmo2010.views.score_detail_direct', args = [score.pk, 'update']),
            extra_context = {
                'score': score
            }
        )
    else: return HttpResponseForbidden(_('Forbidden'))
