#!/usr/bin/python
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
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
"""
Copy monitoring
Usage in command line:
    ./file_name monitoring_ig need_comments
    e.g.: ./copy_monitoring.py 49
          ./copy_monitoring.py 50 True

"""

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))
path = "%s/../exmo" % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from copy import deepcopy
from django.contrib.comments.models import Comment

from exmo2010.models import *


def copy_monitoring(monitoring_pk, need_comment=False):
    m_src = Monitoring.objects.get(pk=monitoring_pk)
    #create monitoring
    m_name = '%s_copy' % m_src.name
    m = deepcopy(m_src)
    m.pk = None
    m.name = m_name
    m.status = MONITORING_RATE
    m.save()
    print "Monitoring ID - %d" % m.pk

    organization_map = {}
    parameter_map = {}

    #tasks
    tasks = Task.objects.filter(organization__monitoring=m_src)
    for i, t in enumerate(tasks):
        if (i+1) % 5 == 0:
            print "%d(%d)" % (i+1, len(tasks))
        org = deepcopy(t.organization)
        org.pk = None
        org.monitoring = m
        org.inv_code = generate_inv_code(6)
        try:
            org.save()
        except:
            org = Organization.objects.get(name=org.name, monitoring=m)
        organization_map[t.organization.pk] = org.pk
        task = deepcopy(t)
        task.pk = None
        task.organization = org
        task.save()
        scores = Score.objects.filter(task=t)
        for s in scores:
            if Parameter.objects.filter(
                    monitoring=m,
                    code=s.parameter.code,
            ).exists():
                param = Parameter.objects.get(
                    monitoring=m,
                    code=s.parameter.code)
            else:
                param = deepcopy(s.parameter)
                param.pk = None
                param.monitoring = m
                param.save()
                param.exclude.clear()
                parameter_map[s.parameter.pk] = param.pk
            score = deepcopy(s)
            score.pk = None
            score.task = task
            score.parameter = param
            score.save()

            if need_comment:
                comments = Comment.objects.for_model(Score).filter(object_pk=s.pk)
                for c in comments:
                    comment = deepcopy(c)
                    comment.pk = None
                    comment.object_pk = score.pk
                    comment.save()

    for param_pk, new_param_pk in parameter_map.iteritems():
        param = Parameter.objects.get(pk=param_pk)
        new_param = Parameter.objects.get(pk=new_param_pk)
        for org_pk in param.exclude.values_list('pk', flat=True):
            if organization_map in [org_pk]:
                new_param.exclude.add(Organization.objects.get(pk=organization_map[org_pk]))


if __name__ == "__main__":
    try:
        args = len(sys.argv[1:3])
        m_id = sys.argv[1]
        if args == 2:
            comm = sys.argv[2]
            copy_monitoring(m_id, comm)
        elif args == 1:
            copy_monitoring(m_id)
    except IndexError:
        print "Enter monitoring ID in command line!"
    except Exception as e:
        print e
    finally:
        sys.exit(0)
