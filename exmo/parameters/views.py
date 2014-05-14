# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
import json

from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.forms import HiddenInput, Media, IntegerField
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import UpdateView, DeleteView

from core.views import LoginRequiredMixin
from exmo2010.forms import CORE_MEDIA
from exmo2010.mail import mail_param_edited
from exmo2010.models import Parameter, Task
from modeltranslation_utils import CurLocaleModelForm


def parameter_exclude(request, parameter_pk, task_pk):
    param = get_object_or_404(Parameter, pk=parameter_pk)
    if not request.user.has_perm('exmo2010.exclude_parameter', param):
        raise PermissionDenied
    task = get_object_or_404(Task, pk=task_pk)
    if task.organization not in param.exclude.all():
        param.exclude.add(task.organization)
    base_url = reverse('exmo2010:task_scores', args=[task.pk])
    return HttpResponseRedirect('%s?%s' % (base_url, request.GET.urlencode()))


class ParameterMixin(LoginRequiredMixin):
    context_object_name = 'param'

    def get_success_url(self):
        base_url = reverse('exmo2010:task_scores', args=[self.task.pk])
        return '%s?%s' % (base_url, self.request.GET.urlencode())


class ParamEditView(ParameterMixin, UpdateView):
    template_name = "parameter_form.html"

    def get_context_data(self, **kwargs):
        context = super(ParamEditView, self).get_context_data(**kwargs)
        return dict(context, media=CORE_MEDIA + Media(css={"all": ["exmo2010/css/selector.css"]}))

    def get_object(self):
        self.task = get_object_or_404(Task, pk=self.kwargs["task_pk"])
        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.task.organization.monitoring):
            raise PermissionDenied

        if 'parameter_pk' in self.kwargs:
            # Existing parameter edit page
            param = get_object_or_404(Parameter, pk=self.kwargs['parameter_pk'])
        else:
            # New parameter page
            param = Parameter(monitoring=self.task.organization.monitoring)

        return param

    def get_form_class(self):
        widgets = {'exclude': FilteredSelectMultiple('', is_stacked=False)}
        form_class = modelform_factory(model=Parameter, form=CurLocaleModelForm, widgets=widgets)

        # Limit organizations choices to this monitoring.
        form_class.base_fields['exclude'].queryset = self.object.monitoring.organization_set.all()

        # Explicitly add "monitoring" field to the form.
        # This is workaround for Django bug 13091 https://code.djangoproject.com/ticket/13091
        #
        # 1) We want "monitoring" value to be constant, as we set it explicitly on parameter instance in `get_object`
        #    method. We have to prevent changing model instance's "monitoring" attribute during form validation.
        #    - This is a security requirement as we only check permissions on monitoring that we got from url arguments.
        #      Actually now there is no threat as any expertA is able to edit any parameter. But it will be if\when
        #      we will implement more granular permissions model.
        # 2) Also we want to properly validate unique_together constraints involving "monitoring" field on the model.
        #    - Failing to do that will raise IntegrityError on instance saving.
        #
        # The problem is that django will exclude all unique_together checks involving "monitoring" field if this field
        # is absent in the form (we fail to meet goal 2). But if we just add the "monitoring" field to the form - it
        # will be possible to change instance's initial "monitoring" submitting the forged form data (we fail to meet
        # goal 1).
        #
        # To meet both goals we have to:
        # 1) Set editable=False attribute on model field.
        # 2) Explicitly add "monitoring" field with some nonfalse initial value to the form.
        #
        # Setting editable=False on model field, will prevent instance.monitoring from getting changed during form
        # validation.
        # Adding explicit monitoring field will force modelform to validate unique_together constraints involving
        # monitoring on Parameter instance.
        #
        form_class.base_fields['monitoring'] = IntegerField(widget=HiddenInput, initial=1)

        return form_class

    def form_valid(self, form):
        param = form.save()
        if "submit_and_send" in self.request.POST:
            mail_param_edited(param, form)
        return HttpResponseRedirect(self.get_success_url())


class ParamDeleteView(ParameterMixin, DeleteView):
    template_name = "exmo2010/parameter_confirm_delete.html"

    def get_object(self):
        self.task = get_object_or_404(Task, pk=self.kwargs["task_pk"])
        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.task.organization.monitoring):
            raise PermissionDenied

        return get_object_or_404(Parameter, pk=self.kwargs['parameter_pk'])


@csrf_exempt
def get_pc(request):
    """
    AJAX-вьюха для получения списка критериев, отключенных у параметра.

    """
    if request.user.is_authenticated() and request.method == "POST" and request.is_ajax():
        try:
            parameter = Parameter.objects.get(pk=request.POST.get("p_id"))
        except ObjectDoesNotExist:
            raise Http404
        skip_list = []
        if not parameter.complete:
            skip_list.append(2)
        if not parameter.topical:
            skip_list.append(3)
        if not parameter.accessible:
            skip_list.append(4)
        if not parameter.hypertext:
            skip_list.append(5)
        if not parameter.document:
            skip_list.append(6)
        if not parameter.image:
            skip_list.append(7)

        return HttpResponse(json.dumps(skip_list), mimetype='application/json')
    else:
        raise Http404
