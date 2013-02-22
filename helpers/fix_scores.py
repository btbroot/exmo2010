#!/usr/bin/python
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012, 2013 Institute for Information Freedom Development
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

'''
Fix scores for error in validation (sa: #189).
'''

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from exmo2010.models import Score
for s in Score.objects.all():
    if not s.found:
        s.complete=None
        s.topical=None
        s.accessible=None
        s.hypertext=None
        s.document=None
        s.image=None
        s.completeComment=""
        s.topicalComment=""
        s.accessibleComment=""
        s.hypertextComment=""
        s.documentComment=""
        s.imageComment=""
        s.clean()
        s.save()
