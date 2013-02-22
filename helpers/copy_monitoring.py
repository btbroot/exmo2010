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
Copy monitoring
'''

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))
path = "%s/../exmo" % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from django.contrib.comments.models import Comment
import exmo2010.models as em
from copy import deepcopy

NEED_COMMENT=True
NEED_COMMENT=False

def copy_monitoring(monitoring_pk):
    m_src = em.Monitoring.objects.get(pk = monitoring_pk)
    #create monitoring
    m_name = '%s_new' % m_src.name
    m = deepcopy(m_src)
    m.pk = None
    m.name = m_name
    m.status = em.Monitoring.MONITORING_RATE
    m.save()
    print m.pk

    organization_map = {}
    parameter_map = {}

    #tasks
    tasks = em.Task.objects.filter(organization__monitoring = m_src, status= em.Task.TASK_APPROVED)
    for t in tasks:
        org = deepcopy(t.organization)
        org.pk = None
        org.monitoring = m
        org.inv_code = em.generate_inv_code(6)
        org.save()
        organization_map[t.organization.pk] = org.pk
        task = deepcopy(t)
        task.pk = None
        task.organization = org
        task.save()
        scores = em.Score.objects.filter(task = t)
        for s in scores:
            if em.Parameter.objects.filter(
                monitoring = m,
                code = s.parameter.code,
            ).exists():
                param = em.Parameter.objects.get(
                    monitoring = m,
                    code = s.parameter.code)
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

            if NEED_COMMENT:
                comments = Comment.objects.for_model(em.Score).filter(object_pk=s.pk)
                for c in comments:
                    comment = deepcopy(c)
                    comment.pk = None
                    comment.object_pk = score.pk
                    comment.save()

    for param_pk, new_param_pk in parameter_map.iteritems():
        param = em.Parameter.objects.get(pk=param_pk)
        new_param = em.Parameter.objects.get(pk=new_param_pk)
        for org_pk in param.exclude.values_list('pk', flat=True):
            if organization_map.has_key(org_pk):
                new_param.exclude.add(em.Organization.objects.get(pk=organization_map[org_pk]))

copy_monitoring(50)
