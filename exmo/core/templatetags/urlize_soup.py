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

from BeautifulSoup import BeautifulSoup
from django import template
from django.utils.html import urlize


register = template.Library()


@register.filter(is_safe=True)
def urlize_soup(value):
    """
    Urlize only text nodes in given html soup, leaving existing anchor tags untouched.
    """

    soup = BeautifulSoup(value)

    for text_node in soup.findAll(text=True):
        if not text_node.findParent('a'):
            text_node.replaceWith(BeautifulSoup(urlize(text_node)))

    return unicode(soup)
