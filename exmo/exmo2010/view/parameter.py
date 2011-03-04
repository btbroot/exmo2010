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
from django.shortcuts import get_object_or_404
from django.views.generic.create_update import update_object, delete_object
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from exmo.exmo2010.models import Parameter, Task
from exmo.exmo2010.forms import ParameterForm
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.core.urlresolvers import reverse



@login_required
def parameter_manager(request, task_id, id, method):
    if not request.user.is_superuser:
        return HttpResponseForbidden(_('Forbidden'))
    task = get_object_or_404(Task, pk = task_id)
    parameter = get_object_or_404(Parameter, pk = id)
    redirect = '%s?%s' % (reverse('exmo.exmo2010.view.score.score_list_by_task', args=[task.pk]), request.GET.urlencode())
    redirect = redirect.replace("%","%%")
    if method == 'delete':
        title = _('Delete parameter %s') % parameter
        return delete_object(
            request,
            model = Parameter,
            object_id = id,
            post_delete_redirect = redirect,
            extra_context = {
                'title': title,
                'task': task,
                }
            )
    else: #update
        title = _('Edit parameter %s') % parameter
        return update_object(
            request,
            form_class = ParameterForm,
            object_id = id,
            post_save_redirect = redirect,
            extra_context = {
                'title': title,
                'task': task,
                }
            )
