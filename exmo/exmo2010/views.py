from exmo.exmo2010.sort_headers import SortHeaders
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import update_object
from django.contrib.auth.decorators import login_required
from exmo.exmo2010.models import Organization, Parameter, Score, Task

@login_required
def parameter_by_organization_list(request, organization_id):
  organization = get_object_or_404(Organization, pk = organization_id)
  return object_list(
    request,
    queryset = Parameter.objects.filter(
      type = organization.type,
    ),
    template_name = 'exmo2010/parameter_by_organization_list.html',
    extra_context = {'organization': organization},
  )

def score_by_organization_parameter_detail(request, organization_id, parameter_id):
  organization = get_object_or_404(Organization, pk = organization_id)
  parameter = get_object_or_404(Parameter, pk = parameter_id, type = organization.type)
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
        }

def score_detail(request, task_id, parameter_id):
    score = Score.objects.get_or_create(task = Task.objects.get(pk=task_id), parameter = Parameter.objects.get(pk = parameter_id))
    return score_detail_direct(request, score[0].pk)

from django.core.urlresolvers import reverse
from reversion import revision
from exmo.exmo2010.helpers import construct_change_message
@revision.create_on_success
def score_detail_direct(request, score_id):
    score = get_object_or_404(Score, pk = score_id)
    if request.method == 'POST':
	form = ScoreForm(request.POST,instance=score)
	message = construct_change_message(request,form, None)
	revision.comment = message
    return update_object(
      request,
      form_class = ScoreForm,
      object_id = score.pk,
      post_save_redirect = reverse('exmo.exmo2010.views.score_list_by_task', args=[score.task.pk])
    )

from django.db.models import Q
def score_list_by_task(request, task_id):
    task = get_object_or_404(Task, pk = task_id)
    queryset = Parameter.objects.filter(Q(type=task.organization.type), ~Q(exclude=task.organization)).extra(
      select={
        'status':'SELECT id FROM %s WHERE task_id = %s and parameter_id = %s.id' % (Score._meta.db_table,task.pk, Parameter._meta.db_table),
      }
    )
    return table(request,
      headers=(
        ('Code', 'code'),
        ('Name', 'name'),
        ('Status', 'status'),
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
  )
  if 'extra_context' not in kwargs:
    kwargs['extra_context'] = {}
  kwargs['extra_context'].update(
    {
      'headers': sort_headers.headers(),
    }
  )
  return object_list(request, **kwargs)

