#!/usr/bin/python

'''
Set max score for topical and complete for techinical rating
'''


import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from exmo.exmo2010.models import Score
from exmo.exmo2010.models import Score, Monitoring

monitoring = Monitoring.objects.get(pk=1)

for s in Score.objects.filter(task__monitoring = monitoring):
    if s.found:
        if s.parameter.type.topical:
            s.topical = 3
        if s.parameter.type.complete:
            s.complete = 3
        s.clean()
        s.save()
