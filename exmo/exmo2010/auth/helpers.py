# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
from django.contrib.auth.models import Group, User
from exmo2010 import models as em


def monitoring_permission(user, priv, monitoring):
    if priv in ('exmo2010.admin_monitoring', 'exmo2010.create_monitoring', 'exmo2010.edit_monitoring', 'exmo2010.delete_monitoring'):
        if user.is_active:
            if user.profile.is_manager_expertB: return True
    if priv == 'exmo2010.view_monitoring':
        if user.is_active:
            if user.profile.is_expertA or user.profile.is_manager_expertB: return True
        #monitoring have one approved task for anonymous and publish
        if em.Task.approved_tasks.filter(organization__monitoring = monitoring).count() > 0 and monitoring.is_publish: return True
        if user.is_active: #minimaze query
            profile = user.profile
            if profile.is_expert and em.Task.objects.filter(organization__monitoring = monitoring, user = user).count() > 0 and monitoring.is_active : return True
            elif profile.is_organization \
              and em.Task.approved_tasks.filter(organization__monitoring = monitoring, organization__in = profile.organization.all()).count() > 0 \
              and (monitoring.is_interact or monitoring.is_result):
                return True
    if priv == 'exmo2010.rating_monitoring':
        if user.is_active:
            if user.profile.is_expertA or user.profile.is_manager_expertB: return True
        if em.Task.approved_tasks.filter(organization__monitoring = monitoring).count() > 0 and monitoring.is_publish: return True
    return False



def task_permission(user, priv, task):
    if user.is_active:
        if user.profile.is_expertA or user.profile.is_manager_expertB: return True
    if priv == 'exmo2010.view_task':
        if task.approved and task.organization.monitoring.is_publish: return True
        if user.is_active:
            profile = user.profile
            if profile.is_expert and task.user == user: return True
            if profile.is_expert:
                if task.organization.monitoring.is_revision and task.checked:
                    return True
                return user.has_perm('exmo2010.fill_task', task)
            elif profile.is_organization or profile.is_customer:
                if task.organization in profile.organization.all() and task.approved: return True
        elif task.approved and user.has_perm('exmo2010.view_monitoring', task.organization.monitoring):
            return True #anonymous user
    elif priv == 'exmo2010.close_task':
        if task.open and task.user == user and task.organization.monitoring.is_rate: return True
    elif priv == 'exmo2010.check_task':
        if task.ready and task.user == user and task.organization.monitoring.is_rate: return True
    elif priv == 'exmo2010.open_task':
        if task.ready and task.user == user and task.organization.monitoring.is_rate: return True
    elif priv == 'exmo2010.fill_task': #create_score
        if (task.open or task.checked) and task.user == user and (task.organization.monitoring.is_rate or task.organization.monitoring.is_revision): return True
        if task.user == user and task.organization.monitoring.is_interact: return True
    elif priv == 'exmo2010.comment_score':
        if user.is_active:
            profile = user.profile
            if profile.is_expertB and task.user == user and \
                (task.organization.monitoring.is_interact or task.organization.monitoring.is_result):
                    return True
            if profile.is_organization and \
                user.has_perm('exmo2010.view_task', task) and \
                task.organization in profile.organization.all() and \
                task.organization.monitoring.is_interact:
                    return True
    return False



def score_permission(user, priv, score):
    if priv == 'exmo2010.view_score':
        if score.task.organization not in score.parameter.exclude.all():
            return user.has_perm('exmo2010.view_task', score.task)
    elif priv == 'exmo2010.edit_score':
        if score.task.organization not in score.parameter.exclude.all():
            return user.has_perm('exmo2010.fill_task', score.task)
    elif priv == 'exmo2010.delete_score':
        return user.has_perm('exmo2010.fill_task', score.task)
    elif priv == 'exmo2010.comment_score':
        return user.has_perm('exmo2010.comment_score', score.task)
    elif priv == 'exmo2010.view_comment_score':
        if user.is_active:
            profile = user.profile
            if user.profile.is_expertA or user.profile.is_manager_expertB: return True
            if profile.is_organization and user.has_perm('exmo2010.view_task', score.task) and score.task.organization in profile.organization.all():
                return True
            elif profile.is_expert and user.has_perm('exmo2010.view_task', score.task) and score.task.user == user:
                return True
    elif priv == 'exmo2010.add_claim':
        if user.is_active:
            if user.profile.is_expertA or user.profile.is_manager_expertB: return True
            if user.profile.is_expert and score.task.organization.monitoring.is_revision and score.task.checked: return True
    elif priv == 'exmo2010.view_claim':
        return user.has_perm('exmo2010.add_claim', score) or user == score.task.user
    return False



def organization_permission(user, priv, organization):
    '''
    strange permission.
    don't know why we need see organization without tasks for this organization.
    don't use this. generate organization list from tasks list and exmo2010.view_task
    '''
    if priv == 'exmo2010.view_organization':
        if user.is_active:
            if user.profile.is_expertA or user.profile.is_manager_expertB: return True
            profile = user.profile
            if profile.is_expertB:
                if em.Task.objects.filter(organization = organization, user = user).count() > 0: return True
            elif (profile.is_organization or profile.is_customer) and profile.organization.filter(pk = organization.pk).count() > 0: return True
    return False



def parameter_permission(user, priv, parameter):
    if priv == 'exmo2010.exclude_parameter':
        if user.is_active:
            if user.profile.is_expertA or user.profile.is_manager_expertB: return True
            if user.profile.is_expertB \
              and (parameter.monitoring.is_rate or parameter.monitoring.is_interact or parameter.monitoring.is_revision):
                return True
    return False



def check_permission(user, priv, context = None):
    '''check user permission for context'''
    if context is None:
        return False
    func = eval(context._meta.object_name.lower() + '_permission')
    return func(user, priv, context)
