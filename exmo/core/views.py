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
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator


def login_required_on_deny(function):
    """
    Decorator for views that checks that the user is anonymous and redirecting
    to the log-in page in this case if function raised PermissionDenied exception.
    """
    @wraps(function)
    def decorator(request, *args, **kwargs):
        if request.user.is_anonymous():
            try:
                return function(request, *args, **kwargs)
            except PermissionDenied:
                return redirect_to_login(request.get_full_path())
        else:
            return function(request, *args, **kwargs)

    return decorator


class LoginRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class LoginRequiredOnDeny(object):
    @method_decorator(login_required_on_deny)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredOnDeny, self).dispatch(*args, **kwargs)
