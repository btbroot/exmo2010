# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
from exmo.exmo2010.forms import UserForm, UserProfileForm
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
def user_profile(request, id=None):
    if id:
        _user = get_object_or_404(User, pk = id)
    else:
        _user = request.user
    messages = []
    if not request.user.is_superuser and request.user != _user:
        return HttpResponseForbidden(_('Forbidden'))
    if request.method == 'POST':
        uform = UserForm(request.POST, instance = _user)
        pform = UserProfileForm(request.POST, instance = _user.profile)
        if uform.is_valid() and pform.is_valid():
            user = uform.save()
            profile = pform.save()
            redirect = reverse('exmo.exmo2010.view.user.user_profile', args=[user.pk])
            messages.append(_("The %(verbose_name)s was updated successfully.") %\
                                    {"verbose_name": user.profile._meta.verbose_name})
    else:
        uform = UserForm(instance = _user)
        pform = UserProfileForm(instance = _user.profile)
    return render_to_response(
        'exmo2010/user_form.html',
        {
            'uform': uform,
            'pform': pform,
            'object': _user,
            'messages': messages,
        },
        context_instance=RequestContext(request))
