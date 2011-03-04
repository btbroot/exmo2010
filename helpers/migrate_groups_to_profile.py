#!/usr/bin/python

'''
Migrate from group role system for organizations to profile
'''

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from exmo.exmo2010.models import Organization
from django.contrib.auth.models import User
from django.contrib.auth.models import Group

users = User.objects.filter(groups__name='organizations')

for user in users:
    for group in user.groups.all():
        try:
            org = Organization.objects.get(keyname = group.name)
        except Organization.DoesNotExist:
            continue
        else:
            profile = user.get_profile()
            profile.organization.add(org)
