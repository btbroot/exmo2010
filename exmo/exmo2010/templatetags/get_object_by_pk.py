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
get_object_by_pk возвращает объект по имени класса и pk
"""

from django.template import Library, Node
from django.db.models import get_model
from django.template import Variable, resolve_variable
from django import template


register = Library()

class ObjectByPk(Node):
    def __init__(self, model, pk, varname):
        self.pk, self.varname = pk, varname
        self.model = get_model(*model.split('.'))

    def render(self, context):
        pk_id = resolve_variable(self.pk, context)
        try:
            context[self.varname] = self.model._default_manager.select_related().get(pk=pk_id)
        except self.model.DoesNotExist:
            context[self.varname] = None
        return ''

def get_object_by_pk(parser, token):
    bits = token.contents.split()
    if len(bits) != 5:
        raise template.TemplateSyntaxError, "get_object_by_pk tag takes exactly four arguments"
    if bits[3] != 'as':
        raise template.TemplateSyntaxError, "third argument to get_object_by_pk tag must be 'as'"
    return ObjectByPk(bits[1], bits[2], bits[4])

get_object_by_pk = register.tag(get_object_by_pk)
