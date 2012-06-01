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
from django.contrib import messages

@csrf_protect
def user_profile(request, id=None):
    if id:
        _user = get_object_or_404(User, pk = id)
    else:
        _user = request.user
    if not request.user.is_superuser and request.user != _user:
        return HttpResponseForbidden(_('Forbidden'))

    uform = pform = None

    if request.user.is_active:
        if request.method == 'POST':
            uform = UserForm(request.POST, instance = _user)
            pform = UserProfileForm(request.POST, instance = _user.profile)
            if uform.is_valid() and pform.is_valid():
                user = uform.save()
                profile = pform.save()
                if id:
                    redirect = reverse('exmo2010:user_profile', args=[user.pk])
                else:
                    redirect = reverse('exmo2010:user_profile')
                messages.add_message(request, messages.INFO, _("The %(verbose_name)s was updated successfully.") %\
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
            'id': id,
        },
        context_instance=RequestContext(request))

from django.contrib.auth.views import password_change

def exmo_password_change(request, **kwargs):
    kwargs['template_name'] = 'exmo2010/password_change_form.html'
    kwargs['post_change_redirect'] = reverse('exmo2010:password_change_done')
    return password_change(request, **kwargs)

from admin_tools.dashboard.models import DashboardPreferences
@csrf_protect
def user_reset_dashboard(request):
    if request.method == 'POST':
        if request.user.is_active:
            try:
                pref = DashboardPreferences.objects.get(dashboard_id = 'exmo2010', user = request.user)
                pref.data = '{}'
                pref.save()
            except DashboardPreferences.DoesNotExist:
                pass
        messages.add_message(request, messages.INFO, _('Dashboard preferences was reset.'))
        return HttpResponseRedirect(reverse('exmo2010:user_profile'))
    else:
        return HttpResponseForbidden(_('Forbidden'))
