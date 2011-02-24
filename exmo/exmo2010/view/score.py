# This file is part of EXMO2010 software.
# Copyright 2010-2011 Al Nikolov
# Copyright 2010-2011 Institute for Information Freedom Development
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
from exmo.exmo2010.forms import ScoreForm
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import update_object, create_object, delete_object
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from exmo.exmo2010.models import Organization, Parameter, Score, Task, Category, Subcategory
from exmo.exmo2010.models import Monitoring, Claim
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.template import RequestContext
from django.http import HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_protect

@login_required
def score_detail(request, task_id, parameter_id):
    task = get_object_or_404(Task, pk = task_id)
    parameter = get_object_or_404(Parameter, pk = parameter_id)
    redirect = "%s?%s#parameter_%s" % (reverse('exmo.exmo2010.view.score.score_list_by_task', args=[task.pk]), request.GET.urlencode(), parameter.group.fullcode())
    redirect = redirect.replace("%","%%")
    if request.user.has_perm('TASK_EXPERT', task):
      return create_object(
        request,
        form_class = ScoreForm,
        post_save_redirect = redirect,
        extra_context = {
          'task': task,
          'parameter': parameter,
          'title': parameter,
          }
      )
    else:
      return HttpResponseForbidden(_('Forbidden'))



from reversion import revision
from exmo.exmo2010.helpers import construct_change_message
@revision.create_on_success
@login_required
def score_detail_direct(request, score_id, method='update'):
    score = get_object_or_404(Score, pk = score_id)
    redirect = "%s?%s#parameter_%s" % (reverse('exmo.exmo2010.view.score.score_list_by_task', args=[score.task.pk]), request.GET.urlencode(), score.parameter.group.fullcode())
    redirect = redirect.replace("%","%%")
    if method == 'delete':
      title = _('Delete score %s') % score.parameter
      if request.user.has_perm('TASK_EXPERT', score.task):
        return delete_object(request, model = Score, object_id = score.pk, post_delete_redirect = redirect, extra_context = {'title': title})
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'update':
      title = _('Edit score %s') % score.parameter
      if request.user.has_perm('TASK_EXPERT', score.task):
        if request.method == 'POST':
            form = ScoreForm(request.POST,instance=score)
            message = construct_change_message(request,form, None)
            revision.comment = message
            if score.active_claim:
                if form.changed_data:
                    score.close_claim(request.user)
                else:
                    return HttpResponse(_('Have active claim, but no data changed'))
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
          'title': title,
        }
      )
    elif method == 'view':
      if not check_permission(request.user, 'TASK_VIEW', score.task): return HttpResponseForbidden(_('Forbidden'))
      title = _('View score %s') % score.parameter
      return object_detail(
        request,
        queryset = Score.objects.all(),
        object_id = score.pk,
        extra_context = {
          'task': score.task,
          'parameter': score.parameter,
          'title': title,
          'view': True,
        }
      )
    else: return HttpResponseForbidden(_('Forbidden'))


@login_required
def score_list_by_task(request, task_id, report=None):
    task = get_object_or_404(Task, pk = task_id)
    task = Task.objects.extra(select = {'complete': Task._complete}).get(pk = task_id)
    title = _('Score list for %s') % ( task.organization.name )
    if check_permission(request.user, 'TASK_VIEW', task):
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
          (_('Code'), None, None, None, None),
          (_('Name'), 'name', 'name', None, None),
          (_('Found'), None, None, None, None),
          (_('Complete'), None, None, None, None),
          (_('Topical'), None, None, None, None),
          (_('Accessible'), None, None, None, None),
          (_('HTML'), None, None, None, None),
          (_('Document'), None, None, None, None),
          (_('Image'), None, None, None, None),
          (_('Action'), None, None, None, None),
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



@csrf_protect
@login_required
def score_add_comment(request, score_id):
    score = get_object_or_404(Score, pk = score_id)
    if check_permission(request.user, 'SCORE_COMMENT', score):
        return render_to_response(
                'exmo2010/score_comment_form.html',
                {
                    'score': score,
                    'title': _('Add new comment'),
                },
                context_instance=RequestContext(request),
                )
    else: return HttpResponseForbidden(_('Forbidden'))