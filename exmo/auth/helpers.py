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
import re
from types import NoneType

from django.db.models import Q

from exmo2010.models import Task, Score, Parameter, ObserversGroup
from exmo2010.models.monitoring import Monitoring, PRE, RATE, RES, INT, PUB, FIN


def perm_filter(user, priv, queryset):
    if priv == 'view_monitoring':
        if user.is_superuser or user.is_expertA:
            return queryset

        published = Q(status=PUB, hidden=False)
        can_observe = Q()
        if user.is_active and ObserversGroup.objects.filter(users=user).exists():
            can_observe = Q(observersgroup__users=user)

        if user.is_expertB:
            own = Q(organization__task__user=user) & ~Q(status=PRE)
        elif user.is_organization:
            orgs = user.profile.organization.filter(task__status=Task.TASK_APPROVED)
            own = Q(status__in=(INT, FIN, PUB), organization__in=orgs)
        else:
            own = Q()

        return queryset.filter(published | own | can_observe).distinct()

    if priv == 'view_task':
        if user.is_expertA:
            return queryset
        elif user.is_expertB:
            return queryset.filter(user=user)


def monitoring_permission(user, priv, monitoring):
    phase = monitoring.status

    if priv in ('admin_monitoring', 'edit_monitoring'):
        if user.is_expertA:
            return True

    if priv == 'delete_monitoring':
        if user.is_expertA and not phase == PUB:
            return True

    if priv == 'view_monitoring':
        if user.is_superuser or user.is_expertA:
            return True
        elif phase == PUB and not monitoring.hidden:
            return True
        elif user.is_expertB and phase != PRE and \
                user.task_set.filter(organization__monitoring=monitoring).exists():
            return True
        elif user.is_organization and Task.approved_tasks.filter(
                organization__monitoring=monitoring,
                organization__monitoring__status__in=(INT, FIN, PUB),
                organization__in=user.profile.organization.all()).exists():
            return True
        elif phase in (INT, FIN) and user.is_active and \
                ObserversGroup.objects.filter(monitoring=monitoring, users=user).exists():
            return True

    return False


def task_permission(user, priv, task):
    if priv not in existing_permissions(task):
        return False

    if user.is_expertA:
        return True

    monitoring = task.organization.monitoring
    phase = monitoring.status

    if priv == 'view_task':
        if user.executes(task):
            return True
        elif user.represents(task.organization) or user.observes(task.organization):
            if task.approved and phase in (INT, FIN, PUB):
                return True
        elif task.approved and phase == PUB and not monitoring.hidden:
            # Anonymous or unprivileged user
            return True
    elif priv == 'close_task' and task.open:
        if user.executes(task) and phase == RATE:
            return True
    elif priv == 'open_task' and task.ready:
        if user.executes(task) and phase == RATE:
            return True
    elif priv == 'fill_task':  # create_score
        if user.executes(task):
            if phase in (INT, FIN) or (phase == RATE and task.open):
                return True
    elif priv == 'view_openness':
        if user.is_expertB or user.represents(task.organization) or phase == PUB:
            return True
    if priv == 'view_comments':
        if phase in (INT, FIN, PUB):
            if user.is_expertA or user.executes(task) or user.represents(task.organization):
                return True

    return False


def score_permission(user, priv, score):
    task = score.task
    monitoring = task.organization.monitoring
    phase = monitoring.status

    if priv == 'view_score':
        return user.has_perm('view_task', task)

    if priv == 'edit_score':
        if user.is_expertA and phase in (RATE, INT, RES, FIN):
            return True
        elif user.executes(task):
            if phase in (INT, FIN) or (phase == RATE and task.open):
                return True

    if priv == 'delete_score':
        if user.executes(task):
            if phase in (INT, FIN) or (phase == RATE and task.open):
                return True

    if priv == 'add_comment':
        if user.is_expertA and phase in (INT, FIN, PUB):
            return True
        elif user.is_expertB and task.user_id == user.pk and phase in (INT, FIN):
            return True
        elif user.represents(task.organization) and task.approved and phase == INT:
            return True

    if priv in ['answer_claim', 'answer_clarification']:
        if user.executes(task) and phase in (RATE, INT, FIN):
            return True

    if priv in ['view_claim', 'view_clarification']:
        if user.is_expertA or user.executes(task):
            return True

    if priv in ['add_claim', 'add_clarification']:
        if user.is_expertA and phase in (RATE, RES):
            return True

    if priv == 'delete_claim':
        if user.is_expertA:
            return True

    return False


def parameter_permission(user, priv, parameter):
    if priv == 'exclude_parameter':
        if user.is_expertA:
            return True
    return False


def check_permission(user, priv, context_obj=None):
    """
    Check user permission for context object or global permissions that has no
    context object.
    """
    priv = re.sub(r'^exmo2010\.', '', priv)  # Remove 'exmo2010.' prefix
    if context_obj is not None:
        # Call object permission handler
        handler = perm_handlers[context_obj.__class__]
        return handler(user, priv, context_obj)
    else:
        # Global permissions
        if priv == 'create_monitoring':
            return user.is_expertA


perm_handlers = {
    Monitoring: monitoring_permission,
    Task: task_permission,
    Score: score_permission,
    Parameter: parameter_permission
}


# all permissions that are used in the project should be defined here
_existing_permissions = {
    NoneType: [  # Global permissions
        'create_monitoring',
    ],
    Monitoring: [
        'view_monitoring',
        'delete_monitoring',
        'edit_monitoring',
        'admin_monitoring',
    ],
    Task: [
        'fill_task',
        'open_task',
        'close_task',
        'view_task',
        'approve_task',
        'view_openness',
        'view_comments',
    ],
    Score: [
        # clarifications
        'view_clarification', 'answer_clarification', 'add_clarification',
        # claims
        'view_claim', 'answer_claim', 'add_claim', 'delete_claim',
        # comments
        'add_comment',
        # score
        'delete_score', 'edit_score', 'view_score'
    ],
    Parameter: ['exclude_parameter']
}


def existing_permissions(obj):
    for perm in _existing_permissions[obj.__class__]:
        yield perm


def get_all_permissions(user, obj):
    for perm in existing_permissions(obj):
        if user.has_perm(perm, obj):
            yield perm
