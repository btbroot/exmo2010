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
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import update_object, create_object, delete_object
from django.contrib.auth.decorators import login_required
from exmo.exmo2010.models import Organization, Parameter, Score, Task

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

from django import forms
from django.utils.safestring import mark_safe
class HorizRadioRenderer(forms.RadioSelect.renderer):
    """ this overrides widget method to put radio buttons horizontally
        instead of vertically.
    """
    def render(self):
            """Outputs radios"""
            return mark_safe(u'\n'.join([u'%s\n' % w for w in self]))

class ScoreForm(forms.ModelForm):
    class Meta:
	model = Score
	widgets = {
	    'found': forms.RadioSelect(renderer=HorizRadioRenderer),
            'complete': forms.RadioSelect(renderer=HorizRadioRenderer),
            'topical': forms.RadioSelect(renderer=HorizRadioRenderer),
            'accessible': forms.RadioSelect(renderer=HorizRadioRenderer),
            'document': forms.RadioSelect(renderer=HorizRadioRenderer),
            'hypertext': forms.RadioSelect(renderer=HorizRadioRenderer),
            'image': forms.RadioSelect(renderer=HorizRadioRenderer),
        }

@login_required
def score_detail(request, task_id, parameter_id):
    task = get_object_or_404(Task, pk = task_id)
    if not task.open and not request.user.is_superuser:
	return HttpResponseForbidden('Task closed')
    return create_object(
      request,
      form_class = ScoreForm,
      post_save_redirect = "%s?%s" % (reverse('exmo.exmo2010.views.score_list_by_task', args=[task.pk]), request.GET.urlencode()),
      extra_context = {
        'create': True,
        'task': task,
        'parameter': get_object_or_404(Parameter, pk = parameter_id),
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
    redirect = "%s?%s" % (reverse('exmo.exmo2010.views.score_list_by_task', args=[score.task.pk]), request.GET.urlencode())
    if method == 'delete':
      if request.user.is_superuser or request.user == score.task.user:
	return delete_object(request, model = Score, object_id = score.pk, post_delete_redirect = redirect)
      else: return HttpResponseForbidden('Forbidden')
    else: #update
      if not score.task.open and not request.user.is_superuser:
	return HttpResponseForbidden('Task closed')
      if request.user.is_superuser or request.user == score.task.user:
        if request.method == 'POST':
	    form = ScoreForm(request.POST,instance=score)
	    message = construct_change_message(request,form, None)
	    revision.comment = message
      else: return HttpResponseForbidden('Forbidden')
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
        ('Name', 'name', 'name', None),
        ('Scores', None, None, None),
        ('Action', None, None, None),
      ),
      queryset=queryset,
      paginate_by=15,
      template_name='exmo2010/score_list.html',
      extra_context={'task': task},
    )

def table(request, headers, **kwargs):
  '''Generic sortable table view'''
  sort_headers = SortHeaders(request, headers)
  kwargs['queryset'] = kwargs['queryset'].order_by(
    sort_headers.get_order_by()
  ).filter(
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
                ('Organization', 'organization__name', 'organization__name', None),
                ('Expert', 'user__username', 'user__username', None),
                ('Open', 'open', 'open', int),
                ('%Complete', 'complete', None, None)
              )
    else:
      queryset = queryset.filter(user = request.user)
    # Or, without Expert
      headers = (
                ('Organization', 'organization__name', 'organization__name', None),
                ('Open', 'open', 'open', int),
                ('%Complete', 'complete', None, None)
              )
    return table(request, headers, queryset = queryset, paginate_by = 5)


from django.http import HttpResponseRedirect
from django.template import RequestContext
@revision.create_on_success
@login_required
def task_manager(request, id, method):
    redirect = '%s?%s' % (reverse('exmo.exmo2010.views.tasks'), request.GET.urlencode())
    if method == 'add':
      if request.user.is_superuser:
	return create_object(request, model = Task, post_save_redirect = redirect)
      else: return HttpResponseForbidden('Forbidden')
    elif method == 'delete':
      task = get_object_or_404(Task, pk = id)
      if request.user.is_superuser:
	return delete_object(request, model = Task, object_id = id, post_delete_redirect = redirect)
      else: return HttpResponseForbidden('Forbidden')
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
	else: return HttpResponseForbidden('Already closed')
      else: return HttpResponseForbidden('Forbidden')
    else: #update
      task = get_object_or_404(Task, pk = id)
      if request.user.is_superuser or request.user == task.user:
        return update_object(request, model = Task, object_id = id, post_save_redirect = redirect)
      else: return HttpResponseForbidden('Forbidden')
