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

"""
 Помощники для бекенда. По помощнику на каждый класс модели.
"""

from exmo2010.models import (Task, Monitoring, Score, Parameter,
                             MONITORING_INTERACTION, MONITORING_FINALIZING, MONITORING_PUBLISHED)


def monitoring_permission(user, priv, monitoring):
    if priv in ('exmo2010.admin_monitoring',
                'exmo2010.create_monitoring',
                'exmo2010.edit_monitoring'):
        if user.is_expertA:
            return True

    if priv == 'exmo2010.delete_monitoring':
        if user.is_expertA and not monitoring.is_published:
            return True

    if priv == 'exmo2010.view_monitoring':
        if Task.approved_tasks.filter(organization__monitoring=monitoring).exists() \
           and monitoring.is_published and not monitoring.hidden:
            return True

        if user.is_superuser or user.is_expertA:
            return True
        elif user.is_expertB and monitoring.is_active and \
                Task.objects.filter(organization__monitoring=monitoring, user=user).exists():
            return True
        elif user.is_organization and Task.approved_tasks.filter(
                organization__monitoring=monitoring,
                organization__monitoring__status__in=(
                    MONITORING_INTERACTION,
                    MONITORING_FINALIZING,
                    MONITORING_PUBLISHED,
                ),
                organization__in=user.profile.organization.all()).exists():
            return True

    return False


def task_permission(user, priv, task):
    if priv not in existing_permissions(task):
        return False

    if user.is_active:
        if user.profile.is_expertA:
            return True
        profile = user.profile

    monitoring = task.organization.monitoring

    if priv == 'exmo2010.view_task':
        if task.approved and monitoring.is_published:
            return True
        if user.is_active:
            if profile.is_expert and task.user == user:
                return True
            if profile.is_expert:
                return user.has_perm('exmo2010.fill_task', task)
            elif profile.is_organization or profile.is_customer:
                if task.organization in profile.organization.all() and task.approved \
                   and user.has_perm('exmo2010.view_monitoring', monitoring):
                    return True
        elif task.approved and user.has_perm('exmo2010.view_monitoring', monitoring):
            return True  # anonymous user
    elif priv == 'exmo2010.close_task' and task.open:
        if task.user == user and monitoring.is_rate:
            return True
    elif priv == 'exmo2010.open_task' and task.ready:
        if task.user == user and monitoring.is_rate:
            return True
    elif priv == 'exmo2010.fill_task':  # create_score
        if task.open and task.user == user and monitoring.is_rate:
            return True
        if task.user == user and (monitoring.is_interact or monitoring.is_finishing):
            return True

    elif priv == 'exmo2010.add_comment_score':
        if user.is_active:
            if monitoring.is_interact or monitoring.is_finishing:
                if profile.is_expertA or (profile.is_expertB and task.user == user):
                    return True

            if profile.is_organization and \
                    user.has_perm('exmo2010.view_task', task) and \
                            task.organization in profile.organization.all() and \
                    monitoring.is_interact:
                return True
    return False


def score_permission(user, priv, score):
    task = score.task
    monitoring = task.organization.monitoring

    if user.is_authenticated():
        profile = user.profile

    if priv == 'exmo2010.view_score':
        if score.task.organization not in score.parameter.exclude.all():
            return user.has_perm('exmo2010.view_task', score.task)

    if priv == 'exmo2010.edit_score':
        if score.task.organization not in score.parameter.exclude.all():
            return user.has_perm('exmo2010.fill_task', score.task)

    if priv == 'exmo2010.delete_score':
        return user.has_perm('exmo2010.fill_task', score.task)

    if priv == 'exmo2010.add_comment_score':
        if user.is_active:
            if (profile.is_expertB and not profile.is_expertA) and (monitoring.is_interact or monitoring.is_finishing):
                return True
            if profile.is_expertA and (monitoring.is_interact or monitoring.is_finishing or monitoring.is_published):
                return True
            if profile.is_organization and monitoring.is_interact:
                return True

    if priv == 'exmo2010.view_comment_score':
        if user.is_active and (monitoring.is_interact or monitoring.is_finishing or monitoring.is_published):
            if profile.is_expertA:
                return True
            if profile.is_expertB and task.user_id == user.id:
                return True
            if profile.is_organization and task.organization in profile.organization.all():
                return True

    if priv == 'exmo2010.close_comment_score':
        if user.is_active:
            if profile.is_expertA and (monitoring.is_interact or monitoring.is_finishing or monitoring.is_published):
                return True

    if priv == 'exmo2010.view_claim_score':
        if user.is_active and not monitoring.is_prepare:
            if profile.is_expertA:
                return True
            if profile.is_expertB and task.user_id == user.id:
                return True

    if priv == 'exmo2010.add_claim_score':
        if user.is_active:
            if profile.is_expertA and not (monitoring.is_prepare or monitoring.is_published):
                return True

    if priv == 'exmo2010.answer_claim_score':
        if user.is_active:
            if (profile.is_expertB and not profile.is_expertA) and not (monitoring.is_prepare or monitoring.is_published):
                return True

    if priv == 'exmo2010.delete_claim_score':
        if user.is_active:
            if profile.is_expertA:
                return True

    if priv == 'exmo2010.view_claim':
        if user.is_active:
            if profile.is_expert and not monitoring.is_prepare:
                return True

    if priv == 'exmo2010.view_clarification_score':
        if user.is_active and not monitoring.is_prepare:
            if profile.is_expertA:
                return True
            if profile.is_expertB and task.user_id == user.id:
                return True

    if priv == 'exmo2010.add_clarification_score':
        if user.is_active:
            if profile.is_expertA and not (monitoring.is_prepare or monitoring.is_published):
                return True

    if priv == 'exmo2010.answer_clarification_score':
        if user.is_active:
            if (profile.is_expertB and not profile.is_expertA) and not (monitoring.is_prepare or monitoring.is_published):
                return True

    return False


def parameter_permission(user, priv, parameter):
    if priv == 'exmo2010.exclude_parameter':
        if user.is_expertA:
            return True
    return False


def check_permission(user, priv, context=None):
    """
    check user permission for context
    врапер для функций выше. точка входа для бекенда авторизации django
    делает eval на имя класса.

    """
    if context is None:
        return False
    func = eval(context._meta.object_name.lower() + '_permission')
    return func(user, priv, context)


# all permissions that are used in the project should be defined here
_existing_permissions = {
    Monitoring: [
        'view_monitoring',
        'delete_monitoring',
        'edit_monitoring',
        'create_monitoring',
        'admin_monitoring',
    ],
    Task: [
        'fill_task',
        'open_task',
        'close_task',
        'view_task',
        'approve_task'
    ],
    Score: [
        # clarifications
        'answer_clarification_score', 'add_clarification_score', 'view_clarification_score',
        # claims
        'view_claim', 'delete_claim_score', 'answer_claim_score', 'add_claim_score', 'view_claim_score',
        # comments
        'close_comment_score', 'view_comment_score', 'add_comment_score',
        # score
        'delete_score', 'edit_score', 'view_score'
    ],
    Parameter: ['exclude_parameter']
}


def existing_permissions(obj):
    for perm in _existing_permissions[obj.__class__]:
        yield 'exmo2010.' + perm


def get_all_permissions(user, obj):
    for perm in existing_permissions(obj):
        if user.has_perm(perm, obj):
            yield perm
