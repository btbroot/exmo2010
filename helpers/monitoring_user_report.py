#!/usr/bin/python

'''
Set max score for topical and complete for techinical rating
'''


import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from exmo.exmo2010.models import Score
from exmo.exmo2010.models import Task
from exmo.exmo2010.models import Monitoring
import django.contrib.auth.models as auth

monitoring = Monitoring.objects.get(pk=5)

from django.db.models import Count
print 'user\t\t\topen\tready\tapproved'
for uid in Task.objects.filter(monitoring = monitoring).values('user').annotate(cuser=Count('user')):
    u = auth.User.objects.get(pk=uid['user'])
    open = Task.objects.filter(user=u, monitoring = monitoring, status=Task.TASK_OPEN).count()
    ready = Task.objects.filter(user=u, monitoring = monitoring, status=Task.TASK_READY).count()
    approved = Task.objects.filter(user=u, monitoring = monitoring, status=Task.TASK_APPROVED).count()
    print '%s\t\t\t%s\t%s\t%s' % (u, open, ready, approved)
