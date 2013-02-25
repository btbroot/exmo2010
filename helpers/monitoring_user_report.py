#!/usr/bin/python
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
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
Set max score for topical and complete for techinical rating
'''


import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from exmo2010.models import Score
from exmo2010.models import Task
from exmo2010.models import Monitoring
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
