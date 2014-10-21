# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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

from django.contrib.auth.decorators import login_required
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.forms import Media, Form, BooleanField, IntegerField
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View, UpdateView, DeleteView

from core.views import LoginRequiredMixin
from exmo2010.forms import CORE_MEDIA
from exmo2010.mail import mail_param_edited
from exmo2010.models import Parameter, Task, Score
from modeltranslation_utils import CurLocaleModelForm


class ParamRelevanceForm(Form):
    param_pk = IntegerField()
    task_pk = IntegerField()

    # NOTE: BooleanField in django has weird meaning of 'required' flag
    # See https://groups.google.com/forum/#!topic/django-developers/cZ-FPUyM_cM
    # Also see BooleanField.to_python() in the code.
    # To allow this field to be False - required has to be False
    set_relevant = BooleanField(required=False)


class PostOrgParamRelevanceView(LoginRequiredMixin, View):
    def post(self, request):
        form = ParamRelevanceForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        param = get_object_or_404(Parameter, pk=form.cleaned_data.get('param_pk'))
        if not request.user.has_perm('exmo2010.exclude_parameter', param):
            raise PermissionDenied
        task = get_object_or_404(Task, pk=form.cleaned_data.get('task_pk'))
        if form.cleaned_data.get('set_relevant'):
            if task.organization in param.exclude.all():
                param.exclude.remove(task.organization)
            score = get_object_or_404(Score, task=task, parameter=param, revision=Score.FINAL)
            return HttpResponseRedirect(reverse('exmo2010:score', args=[score.pk]))
        else:
            if task.organization not in param.exclude.all():
                param.exclude.add(task.organization)
            return HttpResponseRedirect(reverse('exmo2010:task_scores', args=[task.pk]))


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

    def get_object(self, queryset=None):
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

        return form_class

    def form_valid(self, form):
        param = form.save()
        if "submit_and_send" in self.request.POST:
            mail_param_edited(param, form)
        return HttpResponseRedirect(self.get_success_url())


class ParamDeleteView(ParameterMixin, DeleteView):
    template_name = "exmo2010/parameter_confirm_delete.html"

    def get_object(self, queryset=None):
        self.task = get_object_or_404(Task, pk=self.kwargs["task_pk"])
        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.task.organization.monitoring):
            raise PermissionDenied

        return get_object_or_404(Parameter, pk=self.kwargs['parameter_pk'])


@login_required
@csrf_exempt
def ajax_get_pc(request):
    """
    AJAX-вьюха для получения списка критериев, отключенных у параметра.

    """
    if request.method == "POST" and request.is_ajax():
        parameter = get_object_or_404(Parameter, pk=request.POST.get("p_id"))
        skip_list = []
        for index, crit in enumerate(Parameter.OPTIONAL_CRITERIA):
            if not getattr(parameter, crit, None):
                skip_list.append(index+2)

        return HttpResponse(json.dumps(skip_list), mimetype='application/json')

    raise PermissionDenied
