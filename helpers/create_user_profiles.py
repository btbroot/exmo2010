#!/usr/bin/python

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from exmo.exmo2010.models import UserProfile
from django.contrib.auth.models import User

for u in User.objects.all():
    profile, created = UserProfile.objects.get_or_create(user = u)
    profile.save()
