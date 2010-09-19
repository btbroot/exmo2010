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
from django import template
from django.utils.safestring import SafeUnicode
from exmo2010.models import TASK_OPEN, TASK_READY, TASK_APPROVED

register=template.Library()

@register.filter
def has_status(task, status):
        """Returns True/False if the task has given status.
        Usage::
                {% if task|has_status:"TASK_OPEN" %}
                ...
                {% endif %}
        No white space allowed.
        """
        status_list = ['TASK_OPEN', 'TASK_READY', 'TASK_APPROVED']
        if status in status_list:
            if task.status == eval(status): return True
            else: return False
        else:
            raise template.TemplateSyntaxError, "status can be one of '%s'" % ", ".join(status_list)
has_status.is_safe = True
