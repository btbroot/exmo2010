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
from django.contrib.auth.models import User
from django.contrib.comments.signals import comment_was_posted, comment_will_be_posted
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.decorators import available_attrs
from django.utils.translation import ugettext as _
from livesettings import config_value

from accounts.views import get_experts
from bread_crumbs.views import breadcrumbs
from core.tasks import send_email
from custom_comments.models import CommentExmo
from exmo2010.models import Score, UserProfile


def comment_list(request):
    """
    Страница сводного списка комментариев.

    """
    user = request.user
    if not (user.is_active and user.profile.is_expert):
        return HttpResponseForbidden(_('Forbidden'))

    if request.is_ajax():
        comments = user.profile.get_answered_comments()
        return render_to_response(
            'comment_list_table.html',
            {'comments': comments},
            context_instance=RequestContext(request))

    else:
        comments = user.profile.get_filtered_not_answered_comments()
        title = current_title = _('Comments')

        crumbs = ['Home']
        breadcrumbs(request, crumbs)

        return render_to_response('comment_list.html',
                                  {
                                      'current_title': current_title,
                                      'title': title,
                                      'comments': comments,
                                  },
                                  RequestContext(request))


def comment_notification(sender, **kwargs):
    """
    Comments notification.

    """
    comment = kwargs['comment']
    user = comment.user
    request = kwargs['request']
    score = comment.content_object
    admin_rcpt, nonadmin_rcpt = [], []
    admin_users = []

    # Update user.email
    if not user.email and comment.user_email:
        user.email = comment.user_email
        user.save()

    subject = u'%(prefix)s%(monitoring)s - %(org)s: %(code)s' % {
        'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
        'monitoring': score.task.organization.monitoring,
        'org': score.task.organization.name.split(':')[0],
        'code': score.parameter.code,
    }

    # get superusers:
    superusers = User.objects.filter(is_superuser=True, email__isnull=False).exclude(email__exact='')
    admin_users.extend(superusers)

    # get experts A, experts B managers:
    admin_users.extend(get_experts())

    # get experts B:
    if score.task.user.is_active:
        admin_users.extend([score.task.user])

    for user in admin_users:
        if user.is_active and user.email and \
                user.profile.notify_comment_preference['type'] == \
                UserProfile.NOTIFICATION_TYPE_ONEBYONE:
            admin_rcpt.append(user)

    admin_all_comments, admin_one_comment = _comments_lists(admin_rcpt)

    # get organizations:
    nonadmin_users = User.objects.filter(
        userprofile__organization=score.task.organization,
        email__isnull=False,
    ).exclude(email__exact='')

    if len(nonadmin_users) > 1:
        # in PostgreSQL = .distinct('email'), but for MySQL it look like this:
        nonadmin_users = User.objects.filter(email__in=nonadmin_users.values_list('email', flat=True)
                                                                     .order_by('email')
                                                                     .distinct())

    for user in nonadmin_users:
        if user.email and user.email not in admin_rcpt and \
                user.profile.notify_comment_preference['type'] == \
                UserProfile.NOTIFICATION_TYPE_ONEBYONE:
            nonadmin_rcpt.append(user)

    nonadmin_all_comments, nonadmin_one_comment = _comments_lists(nonadmin_rcpt)

    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http',
                         request.get_host(),
                         reverse('exmo2010:score_view',
                         args=[score.pk]))

    expert = _(config_value('GlobalParameters', 'EXPERT'))

    setattr(comment, 'is_expert', comment.is_expert())
    setattr(comment, 'is_superuser', comment.is_superuser())
    setattr(comment, 'legal_name', comment.legal_name())

    context = {
        'comments': [comment],
        'expert': expert,
        'score': score,
        'url': url,
        'user': user,
    }

    if nonadmin_one_comment:
        _send_mails(context, False, subject, nonadmin_one_comment)
    if admin_one_comment:
        _send_mails(context, True, subject, admin_one_comment)

    thread = list(CommentExmo.objects.filter(object_pk=comment.object_pk))
    for item in thread:
        setattr(item, 'is_expert', item.is_expert())
        setattr(item, 'is_superuser', item.is_superuser())
        setattr(item, 'legal_name', item.legal_name())

    thread.append(comment)
    context['comments'] = thread

    if nonadmin_all_comments:
        _send_mails(context, False, subject, nonadmin_all_comments)
    if admin_all_comments:
        _send_mails(context, True, subject, admin_all_comments)


comment_will_be_posted.connect(comment_notification)


def _comments_lists(rcpt):
    """
    Get emails lists for comments thread and single comment.

    """
    thread, comment = [], []
    for user in rcpt:
        if user.profile.notify_comment_preference.get('self_all', False):
            thread.append(user.email)
        else:
            comment.append(user.email)

    return list(set(thread)), list(set(comment))


def _send_mails(context, admin, subject, rcpts):
    """
    Sending comments notification mails.

    """
    # True if superusers, experts A, B, B managers, False if organizations
    context['admin'] = admin

    for rcpt in rcpts:
        "".join(rcpt.split())
        send_email.delay(rcpt, subject, 'score_comment', context=context)


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
