# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
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
from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.comments.signals import comment_was_posted
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden
from django.template.response import TemplateResponse
from django.utils.decorators import available_attrs
from django.utils.translation import ugettext as _

from exmo2010.models import Score


def comment_list(request):
    """
    Страница сводного списка комментариев.

    """
    user = request.user
    if not (user.is_active and user.profile.is_expert):
        return HttpResponseForbidden(_('Forbidden'))

    if request.is_ajax():
        comments = user.profile.get_answered_comments()
        return TemplateResponse(request, 'comment_list_table.html', {'comments': comments})

    else:
        comments = user.profile.get_filtered_not_answered_comments()

        return TemplateResponse(request, 'comment_list.html', {
            'title': _('Comments'),
            'comments': comments,
        })


def comment_change_status(sender, **kwargs):
    """
    Изменение статуса предыдущего комментария после его сохранения.

    """
    from custom_comments.models import CommentExmo
    comment = kwargs['comment']

    if comment.content_type.model == 'score':
        score = Score.objects.get(pk=comment.object_pk)

        previous_comments = CommentExmo.objects.filter(
            object_pk=score.pk).exclude(pk=comment.pk).order_by('-submit_date')

        if comment.user.profile.is_expert:
            for c in previous_comments:
                if c.user.profile.is_organization and \
                   c.status == CommentExmo.OPEN:
                    c.status = CommentExmo.ANSWERED
                    c.save()
                elif c.user.profile.is_expert:
                    break


comment_was_posted.connect(comment_change_status)


def comments_login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Custom decorator with redirecting to specific path.

    """
    actual_decorator = _user_passes_test(
        lambda u: u.is_authenticated(),
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def _user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()

            from django.contrib.auth.views import redirect_to_login
            try:
                score_id = request.POST['object_pk']
                path = '%s' % reverse('exmo2010:score_detail', args=[score_id])
            except AttributeError:
                pass
            return redirect_to_login(path, login_url, redirect_field_name)
        return _wrapped_view
    return decorator
