#!/usr/bin/python

'''
Script create generic groups. Also groups and user organizations.
'''

import os, sys
import random
import hashlib

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

generic_group = ['experts', 'organizations', 'customers']

from exmo.exmo2010.models import Organization, OrganizationType
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
            g = Group.objects.get(name=oo.keyname[:80])
        except Group.DoesNotExist:
            g = Group(name=oo.keyname)
            g.save()

        try:
            u = User.objects.get(username=oo.keyname[:30])
        except User.DoesNotExist:
            u = User(username=oo.keyname)
            u.save()

        u.groups.add(g, organizations_g)
        passwd=hashlib.md5(str(random.randrange(100000,999999))).hexdigest()[:8]
        u.set_password(passwd)
        u.save()
        print u"%s:\nlogin: %s\npassword: %s\n" % (oo, u.username, passwd)
