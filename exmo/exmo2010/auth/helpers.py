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
        if user.is_active and user.userprofile.is_expert and Task.objects.filter(monitoring = monitoring, user = user).count() > 0: return True
    return False



def task_permission(user, priv, task):
    if priv == 'exmo2010.view_task':
        if task.approved: return True
        else:
            if user.userprofile.is_expert and user == task.user: return True
            elif user.userprofile.is_organization:
                try:
                    g = Group.objects.get(name = task.organization.keyname)
                    groups = user.groups.all()
                    if g in groups:
                        return True
                except:
                    return False
    return False



def score_permission(user, priv, score):
    task = score.task
    if user.userprofile.is_organization and task.approved and priv == 'SCORE_COMMENT':
        try:
            g = Group.objects.get(name = task.organization.keyname)
            groups = user.groups.all()
            if g in groups:
                return True
            else:
                return False
        except:
            return False

def organization_permission(user, priv, organization):
    if priv == 'exmo2010.view_organization':
        if user.userprofile.is_expert:
            if Task.objects.filter(organization = organization, user = user).count() > 0: return True
            else: return False
        if (user.userprofile.is_organization or user.userprofile.is_customer) and user.userprofile.organization.filter(pk = organization.pk).count() > 0: return True
    return False


def check_permission(user, priv, context = None):
    '''check user permission for context'''
    if context == None:
        return False
    func = eval(context._meta.object_name.lower() + '_permission')
    return func(user, priv, context)
