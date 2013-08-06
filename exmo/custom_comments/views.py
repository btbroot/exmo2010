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
from datetime import timedelta, datetime
from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.contrib.comments.signals import comment_was_posted, comment_will_be_posted
from custom_comments.models import CommentExmo
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.decorators import available_attrs
from django.utils.translation import ugettext as _
from livesettings import config_value

from bread_crumbs.views import breadcrumbs
from core.helpers import get_experts
from core.tasks import send_email
from exmo2010.models import Organization, Score, Task, UserProfile


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
    comments = [comment]
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

    context = {
        'comments': comments,
        'expert': expert,
        'score': score,
        'url': url,
        'user': user,
    }

    if nonadmin_one_comment:
        _send_mails(context, False, subject, nonadmin_one_comment)
    if admin_one_comment:
        _send_mails(context, True, subject, admin_one_comment)

    context['comments'] = list(CommentExmo.objects.filter(
        object_pk=comment.object_pk
    )) + comments

    if nonadmin_all_comments:
        _send_mails(context, False, subject, nonadmin_all_comments)
    if admin_all_comments:
        _send_mails(context, True, subject, admin_all_comments)


comment_will_be_posted.connect(comment_notification)


def _comments_lists(rcpt):
    """
    Get emails lists for comments branch and single comment.

    """
    branch, comment = [], []
    for user in rcpt:
        if user.profile.notify_comment_preference.get('self_all', False):
            branch.append(user.email)
        else:
            comment.append(user.email)

    return list(set(branch)), list(set(comment))


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


def comment_report(monitoring):
    """
    Вернет словарь с основной статистикой по комментариям.

    """
    from custom_comments.models import CommentExmo

    result = {}
    comments_without_reply = []
    fail_comments_without_reply = []
    fail_soon_comments_without_reply = []
    fail_comments_with_reply = []
    active_organization_stats = []
    total_org = Organization.objects.filter(monitoring=monitoring)
    reg_org = total_org.filter(userprofile__isnull=False)
    start_date = monitoring.interact_date
    end_date = datetime.today()
    time_to_answer = monitoring.time_to_answer

    scores = Score.objects.filter(
        task__organization__monitoring=monitoring)

    iifd_all_comments = CommentExmo.objects.filter(
        content_type__model='score',
        object_pk__in=scores,
        user__in=User.objects.exclude(
            groups__name='organizations')).order_by('submit_date')

    org_all_comments = CommentExmo.objects.filter(
        content_type__model='score',
        object_pk__in=scores,
        user__in=User.objects.filter(
            groups__name='organizations')).order_by('submit_date')

    org_comments = org_all_comments.filter(
        status=CommentExmo.OPEN
    )

    comments_with_reply = org_all_comments.filter(
        status=CommentExmo.ANSWERED
    )

    active_organizations = set([Score.objects.get(
        pk=oco.object_pk).task.organization for oco in org_all_comments])
    for active_organization in active_organizations:
        active_org_comments_count = org_all_comments.filter(
            object_pk__in=scores.filter(
                task__organization=active_organization)).count()
        try:
            task = Task.approved_tasks.get(organization=active_organization)
        except Task.DoesNotExist:
            task = None
        active_organization_stats.append(
            {'org': active_organization,
             'comments_count': active_org_comments_count,
             'task': task})

    active_iifd_person_stats = User.objects.filter(
        comment_comments__pk__in=iifd_all_comments).annotate(
            comments_count=Count('comment_comments'))

    for org_comment in org_comments:
        from core.utils import workday_count
        delta = timedelta(days=1)
        #check time_to_answer
        if workday_count(org_comment.submit_date.date() + delta,
                         end_date) == time_to_answer:
            fail_soon_comments_without_reply.append(org_comment)
        elif workday_count(org_comment.submit_date.date() + delta,
                           end_date) > time_to_answer:
            fail_comments_without_reply.append(org_comment)
        else:
            comments_without_reply.append(org_comment)

    #комментарии без ответа
    result['comments_without_reply'] = comments_without_reply
    #просроченные комментарии без ответа
    result['fail_comments_without_reply'] = fail_comments_without_reply
    #комментарии с ответом
    result['comments_with_reply'] = comments_with_reply
    #комментарии без ответа; срок ответа истечет в течении суток
    result['fail_soon_comments_without_reply'] = fail_soon_comments_without_reply
    #комментарии с ответом, но ответ был позже срока
    result['fail_comments_with_reply'] = fail_comments_with_reply
    #неотвеченные комментарии представителей
    result['org_comments'] = org_comments
    #все комментарии экспертов
    result['org_all_comments'] = org_all_comments
    #статистика активных (оставивших хоть один комментарий) организаций
    #лист словарей: [{'org': org1, 'comments_count': 1}, ...]
    result['active_organization_stats'] = active_organization_stats
    #статистика ответов по экспертам
    result['active_iifd_person_stats'] = active_iifd_person_stats
    #комментарии экспертов
    result['iifd_all_comments'] = iifd_all_comments
    #всего огранизаций
    result['total_org'] = total_org
    #зарегистрированных организаций
    result['reg_org'] = reg_org
    #дата начала взаимодействия
    result['start_date'] = start_date
    #дата окончания отчетного периода
    result['end_date'] = end_date
    #срок ответа на комментарии (в днях)
    result['time_to_answer'] = time_to_answer

    return result


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
