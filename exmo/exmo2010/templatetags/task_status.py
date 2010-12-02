# This file is part of EXMO2010 software.
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
from exmo2010.models import Task
from django import template

register = template.Library()

def task_status(status):
    if status == "open": return Task.TASK_OPEN
    if status == "ready": return Task.TASK_READY
    if status == "approved": return Task.TASK_APPROVED

register.simple_tag(task_status)
