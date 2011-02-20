# This file is part of EXMO2010 software.
# Copyright 2010 Al Nikolov
# Copyright 2010 Institute for Information Freedom Development
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

task_permission(user, priv, task):
    if user.userprofile.is_expert and user == task.user and task.open and priv == 'TASK_EXPERT':
        return True
    if user.userprofile.is_expert and user == task.user and priv == 'TASK_VIEW':
        return True
    elif user.userprofile.is_customer and task.approved and priv == 'TASK_VIEW':
        return True
    elif user.userprofile.is_organization and task.approved and priv == 'TASK_VIEW':
        try:
            g = Group.objects.get(name = task.organization.keyname)
            if g in groups:
                return True
            else:
                return False
        except:
            return False




def check_permission(user, priv, context = None):
    '''check user permission for context'''
    if context == None:
        return False
    groups = user.groups.all()
    if context._meta.object_name == 'Task':

    if context._meta.object_name == 'Score':
        task = context.task
        if user.userprofile.is_organization and task.approved and priv == 'SCORE_COMMENT':
            try:
                g = Group.objects.get(name = task.organization.keyname)
                if g in groups:
                    return True
                else:
                    return False
            except:
                return False

    return False
