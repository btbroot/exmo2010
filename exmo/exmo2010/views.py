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

from django.core.urlresolvers import reverse
def score_detail(request, score_id):
    score = get_object_or_404(Score, pk = score_id)
    return update_object(
      request,
      form_class = ScoreForm,
      object_id = score.pk,
      post_save_redirect = reverse('exmo.exmo2010.views.score_list_by_task', args=[score.task.pk])
    )

def getStatus( anObject ):
    return anObject.status()

from django.template import RequestContext
def score_list_by_task(request, task_id):
    task = get_object_or_404(Task, pk = task_id)
    pk_order = status_order = ''
    if request.GET.get('pk_order','') == '':
	pk_order='-'
    if request.GET.get('status_order','') == '':
	status_order='-'
    if request.GET.get('order_by') == 'pk' and (request.GET.get('pk_order','') in ('','-')):
      order_by = request.GET.get('pk_order','') + 'parameter__' + request.GET.get('order_by','pk')
    else:
      order_by = 'parameter__pk'
    object_list = list(Score.objects.filter(task=task).order_by(order_by))
    if request.GET.get('order_by') == 'status':
      object_list.sort(key=getStatus)
      if status_order == '-':
        object_list.reverse()
    return render_to_response('score_list.html',
      {'task': task, 'object_list': object_list, 'user': request.user, 'pk_order': pk_order, 'status_order': status_order},
      context_instance=RequestContext(request)
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

