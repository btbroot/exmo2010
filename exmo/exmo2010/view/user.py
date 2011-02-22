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
from django.views.generic.create_update import update_object
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseForbidden
from django.core.urlresolvers import reverse



@csrf_protect
@login_required
def user_profile(request, id):
    user = get_object_or_404(User, pk = id)
    if not request.user.is_superuser and request.user != user:
        return HttpResponseForbidden(_('Forbidden'))
    return update_object(
        request,
        form_class = UserForm,
        object_id = user.pk,
        post_save_redirect = reverse('exmo.exmo2010.view.user.user_profile', args=[user.pk]),
        template_name = 'exmo2010/user_form.html',
    )
