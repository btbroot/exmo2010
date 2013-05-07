# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
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
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseForbidden, HttpResponseRedirect, Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import ProcessFormView, ModelFormMixin
from django.views.generic.detail import SingleObjectTemplateResponseMixin
import simplejson
from bread_crumbs.views import breadcrumbs
from exmo2010.forms import CORE_MEDIA
from exmo2010.models import Parameter, Score, Task
from parameters.forms import ParameterForm


class ParameterManagerView(SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):
    model = Parameter
    form_class = ParameterForm
    template_name = "parameter_form.html"
    context_object_name = "object"
    extra_context = {}

    def update(self, request, task):
        title = _('Edit parameter %s') % self.object
        current_title = _('Edit parameter')
        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
        breadcrumbs(request, crumbs, task)
        self.extra_context = {'current_title': current_title,
                              'title': title,
                              'task': task,
                              'media': CORE_MEDIA + ParameterForm().media, }

    def get_redirect(self, request, task):
        redirect = '%s?%s' % (reverse('exmo2010:score_list_by_task', args=[task.pk]), request.GET.urlencode())
        redirect = redirect.replace("%", "%%")
        return redirect

    def get_context_data(self, **kwargs):
        context = super(ParameterManagerView, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

    def get(self, request, *args, **kwargs):
        task = get_object_or_404(Task, pk=self.kwargs["task_id"])
        self.success_url = self.get_redirect(request, task)
        self.object = self.get_object()

        if self.kwargs["method"] == 'delete':
            if not request.user.has_perm('exmo2010.admin_monitoring', task.organization.monitoring):
                return HttpResponseForbidden(_('Forbidden'))
            self.template_name = "exmo2010/parameter_confirm_delete.html"
            title = _('Delete parameter %s') % self.object
            current_title = _('Delete parameter')
            crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
            breadcrumbs(request, crumbs, task)
            self.extra_context = {'current_title': current_title,
                                  'title': title,
                                  'task': task,
                                  'deleted_objects': Score.objects.filter(parameter=self.object), }

        if self.kwargs["method"] == 'exclude':
            if not request.user.has_perm('exmo2010.exclude_parameter', self.object):
                return HttpResponseForbidden(_('Forbidden'))
            if task.organization not in self.object.exclude.all():
                self.object.exclude.add(task.organization)
            return HttpResponseRedirect(self.success_url)

        if self.kwargs["method"] == 'update':
            if not request.user.has_perm('exmo2010.admin_monitoring', task.organization.monitoring):
                return HttpResponseForbidden(_('Forbidden'))
            self.update(request, task)

        return super(ParameterManagerView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        task = get_object_or_404(Task, pk=self.kwargs["task_id"])
        self.success_url = self.get_redirect(request, task)
        self.object = self.get_object()
        if self.kwargs["method"] == 'delete':
            self.object.delete()
            return HttpResponseRedirect(self.get_success_url())
        elif self.kwargs["method"] == 'update':
            self.update(request, task)
            return super(ParameterManagerView, self).post(request, *args, **kwargs)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ParameterManagerView, self).dispatch(*args, **kwargs)


@login_required
def parameter_add(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if not request.user.has_perm('exmo2010.admin_monitoring', task.organization.monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    redirect = '%s?%s' % (reverse('exmo2010:score_list_by_task', args=[task.pk]), request.GET.urlencode())
    redirect = redirect.replace("%", "%%")
    title = _('Add parameter for %s') % task
    form = None
    if request.method == 'GET':
        form = ParameterForm(monitoring=task.organization.monitoring)
    elif request.method == 'POST':
        form = ParameterForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(redirect)

    crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
    breadcrumbs(request, crumbs, task)
    current_title = _('Add parameter')

    return render_to_response(
        'parameter_form.html',
        {
            'form': form,
            'current_title': current_title,
            'title': title,
            'task': task,
            'media': CORE_MEDIA + form.media,
        },
        context_instance=RequestContext(request),
    )


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

        return HttpResponse(simplejson.dumps(skip_list), mimetype='application/json')
    else:
        raise Http404