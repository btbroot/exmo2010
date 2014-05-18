# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
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
from django.test import TestCase
from nose_parameterized import parameterized

from core.templatetags.target_blank import target_blank
from core.templatetags.urlize_soup import urlize_soup


class UrlizeSoupTestCase(TestCase):
    # Should convert plain urls to anchor tags, leaving existing anchors untouched

    @parameterized.expand([
        ('<a><span>X</span>Y</a>Z', '<a><span>X</span>Y</a>Z'),
        ('http://ya.ru', '<a href="http://ya.ru">http://ya.ru</a>')
    ])
    def test_urlize_soup(self, data, expected_result):
        self.assertEqual(urlize_soup(data), expected_result)


class TargetBalnkTestCase(TestCase):
    # Should add target="_blank" to anchor tags

    @parameterized.expand([
        ('<a><span>X</span>Y</a>Z', '<a target="_blank"><span>X</span>Y</a>Z'),
        ('<a target="_blank">http://ya.ru</a>', '<a target="_blank" >http://ya.ru</a>')
    ])
    def test_target_blank(self, data, expected_result):
        self.assertEqual(target_blank(data), expected_result)
