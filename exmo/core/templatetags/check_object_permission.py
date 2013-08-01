# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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
Добавляет тег check_object_permission для проверки прав на объект
"""

from django.template import Library, Node
from django.db.models import get_model
from django.template import Variable, resolve_variable
from django import template


register = Library()

class CheckPerm(Node):
    def __init__(self, priv, obj, varname):
        self.priv = priv
        self.obj = obj
        self.varname = varname

    def render(self, context):
        request = context['request']
        obj = context[self.obj]
        context[self.varname] = request.user.has_perm(self.priv, obj)
        return ''

@register.tag
def check_object_permission(parser, token):
    bits = token.contents.split()
    if len(bits) != 5:
        raise template.TemplateSyntaxError, "check_object_permission tag takes exactly four arguments"
    if bits[3] != 'as':
        raise template.TemplateSyntaxError, "third argument to check_object_permission tag must be 'as'"
    return CheckPerm(bits[1], bits[2], bits[4])
