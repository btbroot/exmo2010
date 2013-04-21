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
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.create_update import update_object, delete_object
import simplejson

from bread_crumbs.views import breadcrumbs
from exmo2010.forms import CORE_MEDIA
from exmo2010.models import Parameter, Score, Task
from parameters.forms import ParameterForm


@login_required
def parameter_manager(request, task_id, parameter_id, method):
    task = get_object_or_404(Task, pk=task_id)
    parameter = get_object_or_404(Parameter, pk=parameter_id)
    redirect = '%s?%s' % (reverse('exmo2010:score_list_by_task', args=[task.pk]), request.GET.urlencode())
    redirect = redirect.replace("%", "%%")
    if method == 'delete':
        if not request.user.has_perm('exmo2010.admin_monitoring', task.organization.monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        title = _('Delete parameter %s') % parameter
        current_title = _('Delete parameter')

        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
        breadcrumbs(request, crumbs, task)

        return delete_object(
            request,
            model=Parameter,
            object_id=parameter_id,
            post_delete_redirect=redirect,
            extra_context={
                'current_title': current_title,
                'title': title,
                'task': task,
                'deleted_objects': Score.objects.filter(parameter=parameter),
            }
        )
    elif method == 'exclude':
        if not request.user.has_perm('exmo2010.exclude_parameter', parameter):
            return HttpResponseForbidden(_('Forbidden'))
        if task.organization not in parameter.exclude.all():
            parameter.exclude.add(task.organization)
        return HttpResponseRedirect(redirect)
    else:  # update
        if not request.user.has_perm('exmo2010.admin_monitoring', task.organization.monitoring):
            return HttpResponseForbidden(_('Forbidden'))
        title = _('Edit parameter %s') % parameter
        current_title = _('Edit parameter')

        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
        breadcrumbs(request, crumbs, task)

        return update_object(
            request,
            form_class=ParameterForm,
            object_id=parameter_id,
            post_save_redirect=redirect,
            extra_context={
                'current_title': current_title,
                'title': title,
                'task': task,
                'media': CORE_MEDIA + ParameterForm().media,
            }
        )


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