#!/usr/bin/python

'''
Fix scores for error in validation (sa: #189).
'''

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from exmo.exmo2010.models import Score
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
