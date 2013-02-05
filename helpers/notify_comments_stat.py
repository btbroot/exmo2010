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
Send comments statistics for admins
'''


import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from django.contrib.comments import models as commentModel
from django.contrib.auth import models as authModel
from django.contrib.sites import models as sitesModel
from exmo2010 import models as exmoModel
from datetime import datetime, timedelta, date
from django.db.models import Q
from exmo2010.utils import workday_count
from django.db.models import Avg, Max, Min, Count

end_date = date.today()

#incremet limit for TODAY
limit = 2+1

m_pk = sys.argv[1]
if m_pk:
    monitoring = exmoModel.Monitoring.objects.get(pk=m_pk)

start_date = monitoring.interact_date

org_for_monitoring = exmoModel.Organization.objects.filter(monitoring = monitoring)
reg_org_for_monitoring = org_for_monitoring.filter(userprofile__isnull = False).distinct()


#get all comments from org
org_comments = commentModel.Comment.objects.filter(
    content_type__model = 'score',
    submit_date__gte = start_date,
    object_pk__in = exmoModel.Score.objects.filter(task__organization__monitoring = monitoring ),
    user__in = authModel.User.objects.filter(groups__name = 'organizations')).order_by('submit_date')

iifd_all_comments = commentModel.Comment.objects.filter(
    content_type__model = 'score',
    submit_date__gte = start_date,
    object_pk__in = exmoModel.Score.objects.filter(task__organization__monitoring = monitoring ),
    user__in = authModel.User.objects.exclude(groups__name = 'organizations')).order_by('submit_date')


active_organizations = set([exmoModel.Score.objects.get(pk = oco.object_pk).task.organization for oco in org_comments])
active_organization_stats = []

for active_organization in active_organizations:
    active_org_comments_count = org_comments.filter(
            object_pk__in = exmoModel.Score.objects.filter(task__organization = active_organization)
        ).count()
    active_organization_stats.append({
        'org': active_organization,
        'comments_count': active_org_comments_count,
        'task': exmoModel.Task.approved_tasks.select_related().get(organization = active_organization)
    })

active_iifd_person_stats = authModel.User.objects.filter(comment_comments__pk__in = iifd_all_comments).annotate(comments_count = Count('comment_comments'))

comments_without_reply = []
fail_comments_without_reply = []
comments_with_reply = []
fail_soon_comments_without_reply = []
fail_comments_with_reply = []

for org_comment in org_comments:
    iifd_comments = iifd_all_comments.filter(
        submit_date__gte = org_comment.submit_date,
        object_pk = org_comment.object_pk,
    ).order_by('submit_date')
    flag=False
    for iifd_comment in iifd_comments:
        if iifd_comment.submit_date >= org_comment.submit_date:
            if workday_count(org_comment.submit_date.date(), iifd_comment.submit_date.date()) <= limit:
                comments_with_reply.append(org_comment)
                flag=True
                break
            elif workday_count(org_comment.submit_date.date(), iifd_comment.submit_date.date()) > limit:
                fail_comments_with_reply.append(org_comment)
                flag=True
                break
    if not flag:
        if limit-1 < workday_count(org_comment.submit_date.date(), end_date) <= limit:
            fail_soon_comments_without_reply.append(org_comment)
        elif workday_count(org_comment.submit_date.date(), end_date) > limit:
            fail_comments_without_reply.append(org_comment)
        else:
            comments_without_reply.append(org_comment)


from django.template import loader, Context
from django.conf import settings

t = loader.get_template('exmo2010/helpers/score_comments_stat.html')
c = Context({
    'start_date': start_date,
    'end_date': end_date,
    'comments_without_reply': comments_without_reply,
    'fail_comments_without_reply': fail_comments_without_reply,
    'fail_comments_with_reply': fail_comments_with_reply,
    'fail_soon_comments_without_reply': fail_soon_comments_without_reply,
    'comments_with_reply': comments_with_reply,
    'org_comments_count': org_comments.count(),
    'total_org_count': org_for_monitoring.count(),
    'reg_org_count': reg_org_for_monitoring.count(),
    'iifd_comments_count': iifd_all_comments.count(),
    'active_organization_stats': active_organization_stats,
    'active_iifd_person_stats': active_iifd_person_stats,
    'limit': limit,
    'site': sitesModel.Site.objects.get(name = 'exmo.svobodainfo.org'),
    })

message = t.render(c)
from django.core.mail import send_mail

subject = "Comment report from %(start_date)s to %(end_date)s for %(monitoring)s" % { 
    'start_date': start_date,
    'end_date': end_date,
    'monitoring': monitoring,
    }

rcpt = [ x[1] for x in settings.ADMINS]
rcpt.append('monitoring-list@svobodainfo.org')
send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, rcpt)
