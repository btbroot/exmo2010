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
Добавляет тег get_all_claim для получения претензий для оценки
"""

from django.template import Library, Node
from django.template import Variable, resolve_variable
from exmo2010.models import Claim

register = Library()

class ClaimByScore(Node):
    def __init__(self, score, varname):
        self.score, self.varname = score, varname

    def render(self, context):
        score = resolve_variable(self.score, context)
        context[self.varname] = Claim.objects.filter(score = score)
        return ''

def get_all_claim(parser, token):
    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError, "get_all_claim tag takes exactly three arguments"
    if bits[2] != 'as':
        raise template.TemplateSyntaxError, "second argument to get_all_claim tag must be 'as'"
    return ClaimByScore(bits[1], bits[3])

get_all_claim = register.tag(get_all_claim)
