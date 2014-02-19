# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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

from django.contrib.auth.models import User
from django.db.models import Count

from core.utils import workday_count
from custom_comments.models import CommentExmo
from exmo2010.models import Organization, Score, Task


def comment_report(monitoring):
    """
    Вернет словарь с основной статистикой по комментариям.

    org_comments - неотвеченные комментарии представителей
    operator_all_comments - комментарии экспертов
    total_org - всего огранизаций
    comments_without_reply - комментарии без ответа
    fail_comments_without_reply - просроченные комментарии без ответа
    comments_with_reply - комментарии с ответом
    fail_soon_comments_without_reply - комментарии без ответа, срок ответа которых истечет в течении суток
    fail_comments_with_reply - комментарии с ответом, но ответ был позже срока
    org_all_comments - все комментарии экспертов
    active_organization_stats - статистика активных организаций (т.е. оставивших хоть один комментарий)
        вернет список словарей: [{'org': org1, 'comments_count': 1}, ...]
    active_operator_person_stats - статистика ответов по экспертам
    organizations_with_representatives - организаций, имеющих хотя бы одного представителя
    start_date - дата начала взаимодействия
    end_date - дата окончания отчетного периода
    time_to_answer - срок ответа на комментарии (в днях)
    monitoring_name - название мониторинга

    """
    comments_without_reply = []
    fail_comments_without_reply = []
    fail_soon_comments_without_reply = []
    fail_comments_with_reply = []
    active_organization_stats = []
    total_org = Organization.objects.filter(monitoring=monitoring)
    organizations_with_representatives = total_org.filter(userprofile__isnull=False).distinct().count()
    total_org = total_org.count()
    monitoring_name = monitoring.name
    time_to_answer = monitoring.time_to_answer
    start_date = monitoring.interact_date
    end_date = datetime.today()

    scores = Score.objects.filter(
        task__organization__monitoring=monitoring)

    operator_all_comments = CommentExmo.objects.filter(
        content_type__model='score',
        object_pk__in=scores,
        user__in=User.objects.exclude(
            groups__name='organizations'))

    org_all_comments = CommentExmo.objects.filter(
        content_type__model='score',
        object_pk__in=scores,
        user__in=User.objects.filter(
            groups__name='organizations'))

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

    active_operator_person_stats = User.objects.filter(
        comment_comments__pk__in=operator_all_comments).annotate(
            comments_count=Count('comment_comments'))

    for org_comment in org_comments:
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

    org_comments = org_comments.count()
    operator_all_comments = operator_all_comments.count()

    return locals()
