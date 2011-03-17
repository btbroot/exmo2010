#!/usr/bin/python
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 Institute for Information Freedom Development
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

import exmo.exmo2010.models as em
def copy_monitoring(monitoring_pk):
    m_src = em.Monitoring.objects.get(pk = monitoring_pk)
    #create monitoring
    m_name = '%s_new' % m_src.name
    m = em.Monitoring(name = m_name, type = m_src.type)
    m.save()

    #parameters
    params = em.Parameter.objects.filter(monitoring = m_src)
    for p in params:
        w = em.ParameterMonitoringProperty.objects.get(monitoring = m_src, parameter = p).weight
        pmp = em.ParameterMonitoringProperty(monitoring = m, parameter = p, weight = w)
        pmp.save()

    #tasks
    tasks = em.Task.objects.filter(monitoring = m_src)
    for t in tasks:
        task = em.Task(
            user = t.user,
            organization = t.organization,
            monitoring = m,
            status = t.status,
            )
        task.save()
        scores = em.Score.objects.filter(task = t)
        for s in scores:
            score = em.Score(
                task = task,
                parameter = s.parameter,
                found = s.found,
                complete = s.complete,
                completeComment = s.completeComment,
                topical = s.topical,
                topicalComment = s.topicalComment,
                accessible = s.accessible,
                accessibleComment = s.accessibleComment,
                hypertext = s.hypertext,
                hypertextComment = s.hypertextComment,
                document = s.document,
                documentComment = s.documentComment,
                image = s.image,
                imageComment = s.imageComment,
                comment = s.comment,
                )
            score.save()


copy_monitoring(1)
