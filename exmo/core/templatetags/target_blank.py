# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
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
import re
from django import template


register = template.Library()


@register.filter(is_safe=True)
def target_blank(value):
    """
    Add 'target="_blank"' attribute to all anchor tags found in the given text.
    Existing 'target' attributes will be overwritten.
    """
    # Clean existing target attributes.
    value = re.sub('(?<=a)([^>]*)(?:target=[\'\"][^\'\"]*[\'\"])([^>]*)>', r'\1\2>', value)
    # Add target="_blank".
    return re.sub('<a([^>]*)>', '<a target="_blank"\\1>', value)
