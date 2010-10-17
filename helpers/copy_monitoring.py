#!/usr/bin/python

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
            closed = t.closed,
            )
        task.save()
        task.approved = t.approved
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


copy_monitoring(3)
