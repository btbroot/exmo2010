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
from datetime import datetime

from django.contrib.auth.models import User

from core.utils import workday_count
from custom_comments.models import CommentExmo
from exmo2010.models import Score, Task


def comment_report(monitoring):
    """
    Вернет словарь с основной статистикой по комментариям.

    expired - list: просроченные комментарии без ответа
    expiring - list: комментарии без ответа, срок ответа которых истечет в течении суток
    pending - list: остальные комментарии без ответа
    num_answered - количество комментариев с ответом (включая просроченные)
    num_answered_late - количество комментариев с просроченным ответом
    num_org_comments - количество комментариев представителей организаций
    num_expert_comments - количество комментариев экспертов
    active_experts - list: активные эксперты (с доп. атрибутом num_comments)
    active_orgs - list: активные организации (dict c ключами 'name', 'expert' и 'num_comments')
    num_orgs_with_user - количество организаций, имеющих хотя бы одного представителя

    """
    org_users = User.objects.filter(userprofile__organization__monitoring=monitoring)
    org_users = set(org_users.distinct().values_list('pk', flat=True))

    scores = Score.objects.filter(task__organization__monitoring=monitoring, task__status=Task.TASK_APPROVED)

    _scores = scores.values_list('pk', 'task__organization_id', 'task__organization__name', 'task__user__username')
    score_org_expert = dict((str(pk), (org_pk, org_name, expert)) for pk, org_pk, org_name, expert in _scores)

    # Dict by pk. Later this will become a list of active_experts and active_orgs.
    dict_active_experts, dict_active_orgs = {}, {}
    non_urgent, urgent, expired = [], [], []
    num_org_comments = num_answered = num_answered_late = 0

    for comment in CommentExmo.objects.filter(object_pk__in=scores).prefetch_related('user'):
        if comment.user.pk in org_users:
            org_pk, org_name, expert = score_org_expert[comment.object_pk]
            dict_active_orgs.setdefault(org_pk, {'num_comments': 0, 'name': org_name, 'expert': expert})
            dict_active_orgs[org_pk]['num_comments'] += 1

            num_org_comments += 1
            if comment.status == CommentExmo.ANSWERED:
                num_answered += 1
                if workday_count(comment.submit_date, comment.answered_date) > monitoring.time_to_answer:
                    num_answered_late += 1
            elif comment.status == CommentExmo.OPEN:
                days_passed = workday_count(comment.submit_date, datetime.today())
                if days_passed == monitoring.time_to_answer:
                    urgent.append(comment)
                elif days_passed > monitoring.time_to_answer:
                    expired.append(comment)
                else:
                    non_urgent.append(comment)
        else:
            # Comment by expert.
            if comment.user.pk in dict_active_experts:
                dict_active_experts[comment.user.pk].num_comments += 1
            else:
                comment.user.num_comments = 1
                dict_active_experts[comment.user.pk] = comment.user

    active_orgs = dict_active_orgs.values()
    active_experts = dict_active_experts.values()
    num_expert_comments = sum(e.num_comments for e in active_experts)
    num_orgs_with_user = monitoring.organization_set.filter(userprofile__isnull=False).distinct().count()

    # Clean unneeded intermediate local variables before returning the rest as result dictionary.
    del scores, _scores, dict_active_experts, dict_active_orgs, org_users
    return locals()
