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

from django.test import TestCase

from nose_parameterized import parameterized

from core.utils import urlize


class UrlizeTestCase(TestCase):
    # should convert plain urls to 'a' tags and add target='_blank'

    @parameterized.expand([
        ('<a><span>X</span>Y</a>Z', '<a target="_blank"><span>X</span>Y</a>Z'),
        ('http://ya.ru', '<a href="http://ya.ru" target="_blank">http://ya.ru</a>')
    ])
    def test_urlize(self, data, expected_result):
        self.assertEqual(urlize(data), expected_result)
