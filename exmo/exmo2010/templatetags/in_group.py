# -*- coding: utf-8 -*-
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

"""
Тег in_group для определения принадлежности пользователя группе
"""

from django import template
from django.utils.safestring import SafeUnicode

register=template.Library()

@register.filter
def in_group(user, group):
        """Returns True/False if the user is in the given group(s).
        Usage::
                {% if user|in_group:"Friends" %}
                or
                {% if user|in_group:"Friends,Enemies" %}
                ...
                {% endif %}
        You can specify a single group or comma-delimited list.
        No white space allowed.
        """
        import re
        if re.search(',', group): group_list = re.sub('\s+','',group).split(',')
        elif re.search(' ', group): group_list = group.split()
        else: group_list = [group]
        user_groups = []
        for group in user.groups.all(): user_groups.append(str(group.name))
        if filter(lambda x:x in user_groups, group_list): return True
        else: return False
in_group.is_safe = True 
