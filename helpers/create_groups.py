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
Script create generic groups.
'''

import os, sys
import random
import hashlib

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

generic_group = ['experts', 'organizations', 'customers']

from exmo2010.models import Organization, OrganizationType
from django.contrib.auth.models import User
from django.contrib.auth.models import Group

for group in generic_group:
    try:
        g = Group.objects.get(name=group)
    except Group.DoesNotExist:
        g = Group(name=group)
        g.save()

#foiv: pk = 1
o = Organization.objects.filter(type=OrganizationType(pk=1))
experts_g = Group.objects.get(name=generic_group[0])
organizations_g = Group.objects.get(name=generic_group[1])
customer_g = Group.objects.get(name=generic_group[2])

for oo in o:
    if oo.keyname:
        try:
            g = Group.objects.get(name=oo.keyname)
        except Group.DoesNotExist:
            g = Group(name=oo.keyname)
            g.save()
