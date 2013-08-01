# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013 Foundation "Institute for Information Freedom Development"
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
from BeautifulSoup import BeautifulSoup
from django import template
from django.utils.html import urlize
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter(is_safe=True, needs_autoescape=True)
def urlize_target_blank(value, limit=None, autoescape=None):
    """
    Urlize with adding 'target="_blank"' attribute to <a> tag.
    Argument: Length to truncate URLs to.

    """
    text = urlize(value, limit, autoescape)
    links = BeautifulSoup(text)

    for a in links.findAll('a'):
        a['target'] = '_blank'

    result = mark_safe(links)

    return result
