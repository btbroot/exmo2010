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
from exmo.exmo2010.forms import UserForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import get_object_or_404, render_to_response

@csrf_protect
@login_required
def user_profile(request, id):
    _user = get_object_or_404(User, pk = id)
    if not request.user.is_superuser and request.user != _user:
        return HttpResponseForbidden(_('Forbidden'))
    if request.method == 'POST':
        form = UserForm(request.POST, instance = _user)
        if form.is_valid():
            user = form.save()
            profile = user.get_profile()
            if profile.is_organization:
                profile.notify_score_change = form.cleaned_data['notify_score_change']
                profile.save()
            redirect = reverse('exmo.exmo2010.view.user.user_profile', args=[user.pk])
    else:
        form = UserForm(instance = _user)
    return render_to_response(
        'exmo2010/user_form.html',
        {
            'form': form,
            'object': _user,
        },
        context_instance=RequestContext(request))
