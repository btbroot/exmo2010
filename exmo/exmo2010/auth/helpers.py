# This file is part of EXMO2010 software.
# Copyright 2010-2011 Al Nikolov
# Copyright 2010-2011 Institute for Information Freedom Development
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
from exmo.exmo2010.models import Task


def monitoring_permission(user, priv, monitoring):
    if priv == 'exmo2010.view_monitoring':
        #monitoring have one approved task for anonymous and have publish_date
        if Task.approved_tasks.filter(monitoring = monitoring).count() > 0 and monitoring.publish_date : return True
        if user.is_active: #minimaze query
            profile = user.get_profile()
            if profile.is_expert and Task.objects.filter(monitoring = monitoring, user = user).count() > 0: return True
    return False



def task_permission(user, priv, task):
    if priv == 'exmo2010.view_task':
        if task.approved and user.has_perm('exmo2010.view_monitoring', task.monitoring): return True #anonymous user
        if user.is_active:
            profile = user.get_profile()
            if profile.is_expert:
                if user == task.user: return True
            elif profile.is_organization or profile.is_customer:
                if task.organization in profile.organization.all(): return True
    elif priv == 'exmo2010.close_task':
        if task.open and task.user == user: return True
    elif priv == 'exmo2010.fill_task': #create_score
        if task.open and task.user == user: return True
    elif priv == 'exmo2010.comment_score':
        if user.is_active:
            profile = user.get_profile()
            if profile.is_organization and user.has_perm('exmo2010.view_task', task): return True
    return False



def score_permission(user, priv, score):
    if priv == 'exmo2010.view_score':
        return user.has_perm('exmo2010.view_task', score.task)
    elif priv == 'exmo2010.edit_score':
        return user.has_perm('exmo2010.fill_task', score.task)
    elif priv == 'exmo2010.delete_score':
        return user.has_perm('exmo2010.fill_task', score.task)
    elif priv == 'exmo2010.comment_score':
        if user.is_active:
            profile = user.get_profile()
            if profile.is_organization and user.has_perm('exmo2010.view_task', score.task): return True
    return False



def organization_permission(user, priv, organization):
    '''
    strange permission.
    don't know why we need see organization without tasks for this organization.
    don't use this. generate organization list from tasks list and exmo2010.view_task
    '''
    if priv == 'exmo2010.view_organization':
        if user.is_active:
            profile = user.get_profile()
            if profile.is_expert:
                if Task.objects.filter(organization = organization, user = user).count() > 0: return True
            elif (profile.is_organization or profile.is_customer) and profile.organization.filter(pk = organization.pk).count() > 0: return True
    return False


def check_permission(user, priv, context = None):
    '''check user permission for context'''
    if context == None:
        return False
    func = eval(context._meta.object_name.lower() + '_permission')
    return func(user, priv, context)
