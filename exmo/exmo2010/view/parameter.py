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
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.generic.create_update import update_object, delete_object

from exmo2010.models import Parameter, Score, Task
from exmo2010.forms import ParameterForm, CORE_MEDIA
from exmo2010.view.breadcrumbs import breadcrumbs


@login_required
def parameter_manager(request, task_id, id, method):
    task = get_object_or_404(Task, pk = task_id)
    parameter = get_object_or_404(Parameter, pk = id)
    redirect = '%s?%s' % (reverse('exmo2010:score_list_by_task', args=[task.pk]), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    if method == 'delete':
        if not request.user.has_perm('exmo2010.admin_monitoring', task.organization.monitoring):
            return HttpResponseForbidden(_('Forbidden'))

        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
        request = breadcrumbs(request, crumbs, task)
        title = _('CHANGE:parameter_manager')

        return delete_object(
            request,
            model = Parameter,
            object_id = id,
            post_delete_redirect = redirect,
            extra_context = {
                'current_title': title,
                'task': task,
                'deleted_objects': Score.objects.filter(parameter = parameter),
                }
            )
    elif method == 'exclude':
        if not request.user.has_perm('exmo2010.exclude_parameter', parameter):
            return HttpResponseForbidden(_('Forbidden'))
        if task.organization not in parameter.exclude.all():
            parameter.exclude.add(task.organization)
        return HttpResponseRedirect(redirect)
    else: #update
        if not request.user.has_perm('exmo2010.admin_monitoring', task.organization.monitoring):
            return HttpResponseForbidden(_('Forbidden'))

        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
        request = breadcrumbs(request, crumbs, task)
        title = _('CHANGE:parameter_manager')

        return update_object(
            request,
            form_class = ParameterForm,
            object_id = id,
            post_save_redirect = redirect,
            extra_context = {
                'current_title': title,
                'task': task,
                'media': CORE_MEDIA + ParameterForm().media,
                }
            )

@login_required
def parameter_add(request, task_id):
    task = get_object_or_404(Task, pk = task_id)
    if not request.user.has_perm('exmo2010.admin_monitoring', task.organization.monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    redirect = '%s?%s' % (reverse('exmo2010:score_list_by_task', args=[task.pk]), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    form = None
    if request.method == 'GET':
        form = ParameterForm(monitoring = task.organization.monitoring)
    elif request.method == 'POST':
        form = ParameterForm(request.POST)
        if form.is_valid():
            parameter = form.save()
            return HttpResponseRedirect(redirect)

    crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
    request = breadcrumbs(request, crumbs, task)
    title = _('CHANGE:parameter_add')

    return render_to_response(
        'exmo2010/parameter_form.html',
        {
            'form': form,
            'current_title': title,
            'task': task,
            'media': CORE_MEDIA + form.media,
        },
        context_instance=RequestContext(request),
    )
