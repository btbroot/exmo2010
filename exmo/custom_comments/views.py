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
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _


@login_required
def comment_list(request):
    """
    Страница сводного списка комментариев.

    """
    user = request.user
    if not user.profile.is_expert:
        raise PermissionDenied

    if request.is_ajax():
        comments = user.profile.get_answered_comments()
        return TemplateResponse(request, 'comment_list_table.html', {'comments': comments})

    else:
        comments = user.profile.get_filtered_not_answered_comments()

        return TemplateResponse(request, 'comment_list.html', {
            'title': _('Comments'),
            'comments': comments,
        })
