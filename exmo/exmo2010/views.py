from django.shortcuts import get_object_or_404
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import update_object
from django.contrib.auth.decorators import login_required
from exmo.exmo2010.models import Organization, Parameter, Score

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

