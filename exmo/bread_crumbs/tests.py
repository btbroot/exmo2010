# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Foundation "Institute for Information Freedom Development"
# Copyright 2013 Al Nikolov
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
#    along with this program.  If not, see <http://www.gnu.usr/licenses/>.
#
from django.test import TestCase
from django.http import HttpRequest
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from nose_parameterized import parameterized
from breadcrumbs.breadcrumbs import Breadcrumbs


class TestBreadcrumbs(TestCase):
    # Scenario: Breadcrumbs data within request
    @parameterized.expand([
        ('Home', '', reverse('exmo2010:index'), 0),
        ('Monitoring', 'Monitoring cycles', reverse('exmo2010:monitoring_list'), 1),
        ('Ratings', 'Ratings', reverse('exmo2010:ratings'), 2),
    ])
    def test_items(self, key, name, url, i):
        # 'breadcrumbs' app name and 'breadcrumbs' function name conflict
        from bread_crumbs.views import breadcrumbs
        request = HttpRequest()
        request.breadcrumbs = Breadcrumbs()

        # WHEN pass to function HttpRequest instance and predefined key
        breadcrumbs(request, [key])

        # THEN request has expected name and url
        name = _(name) if i != 0 else name
        self.assertEqual(request.breadcrumbs[i].name, name)
        self.assertEqual(request.breadcrumbs[i].url, url)


