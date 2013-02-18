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

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"

path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

path = "%s/../exmo" % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from django.template import loader, Context
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites import models as sitesModel
from custom_comments.models import CommentExmo
from exmo2010.models import Organization, Monitoring, Score
from datetime import timedelta, date
from exmo2010.utils import workday_count
from django.db.models import Count

end_date = date.today()

m_pk = sys.argv[1]
monitoring = Monitoring.objects.get(pk=m_pk)

start_date = monitoring.interact_date

limit = time_to_answer = monitoring.time_to_answer

comments_without_reply = []
fail_comments_without_reply = []
comments_with_reply = []
fail_soon_comments_without_reply = []
fail_comments_with_reply = []
org_comments = []
active_organizations = []
active_organization_stats = []
active_iifd_person_stats = []
iifd_all_comments = []

total_org = Organization.objects.filter(monitoring=monitoring)
reg_org = total_org.filter(userprofile__isnull=False)

scores = Score.objects.filter(task__organization__monitoring=monitoring)

iifd_all_comments = CommentExmo.objects.filter(
    status__in=[CommentExmo.OPEN, CommentExmo.ANSWERED],
    content_type__model='score',
    submit_date__gte=start_date,
    object_pk__in=Score.objects.filter(
        task__organization__monitoring=monitoring),
    user__in=User.objects.exclude(
        groups__name='organizations')).order_by('submit_date')

org_comments = CommentExmo.objects.filter(
    status__in=[CommentExmo.OPEN, CommentExmo.ANSWERED],
    content_type__model='score',
    submit_date__gte=start_date,
    object_pk__in=scores,
    user__in=User.objects.filter(
        groups__name='organizations')).order_by('submit_date')

org_all_comments = CommentExmo.objects.filter(
    status__in=[CommentExmo.OPEN, CommentExmo.ANSWERED],
    content_type__model='score',
    submit_date__gte=start_date,
    object_pk__in=Score.objects.filter(
        task__organization__monitoring=monitoring),
    user__in=User.objects.filter(
        groups__name='organizations')).order_by('submit_date')

active_organizations = set([Score.objects.get(
    pk=oco.object_pk).task.organization for oco in org_all_comments])
for active_organization in active_organizations:
    active_org_comments_count = org_comments.filter(
        object_pk__in=Score.objects.filter(
            task__organization__monitoring=monitoring,
            task__organization=active_organization)).count()

    active_organization_stats.append(
        {'org': active_organization,
         'comments_count': active_org_comments_count})

active_iifd_person_stats = User.objects.filter(
    comment_comments__pk__in=iifd_all_comments).annotate(
    comments_count=Count('comment_comments'))

for org_comment in org_comments:
    iifd_comments = iifd_all_comments.filter(
        submit_date__gte=org_comment.submit_date,
        object_pk=org_comment.object_pk,
    ).order_by('submit_date')
    #append comment or not
    delta = timedelta(days=1)
    flag = False
    for iifd_comment in iifd_comments:
        #check that comment from iifd comes after organization
        if iifd_comment.submit_date > org_comment.submit_date:
            #iifd comment comes in time_to_answer
            if workday_count(org_comment.submit_date,
                             iifd_comment.submit_date) <= time_to_answer:
                #pass that this org_comment is with reply
                flag = True
                comments_with_reply.append(org_comment)
                break
            #iifd comment comes out of time_to_answer
            elif workday_count(org_comment.submit_date,
                               iifd_comment.submit_date) > time_to_answer:
                #pass that this org_comment is with reply
                flag = True
                fail_comments_with_reply.append(org_comment)
                break
                #org comment is without comment from iifd
            if not flag:
                #check time_to_answer
                if workday_count(org_comment.submit_date.date() + delta,
                                 end_date) == time_to_answer:
                    fail_soon_comments_without_reply.append(org_comment)
                elif workday_count(org_comment.submit_date.date() + delta,
                                   end_date) > time_to_answer:
                    fail_comments_without_reply.append(org_comment)
                else:
                    comments_without_reply.append(org_comment)

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
    'total_org_count': total_org.count(),
    'reg_org_count': reg_org.count(),
    'iifd_comments_count': iifd_all_comments.count(),
    'active_organization_stats': active_organization_stats,
    'active_iifd_person_stats': active_iifd_person_stats,
    'limit': time_to_answer,
    'site': sitesModel.Site.objects.get(name='exmo.svobodainfo.org'),
})

message = t.render(c)
from django.core.mail import send_mail

subject = "Comment report from %(start_date)s to %(end_date)s for %(monitoring)s" % {
    'start_date': start_date,
    'end_date': end_date,
    'monitoring': monitoring,
}

rcpt = [x[1] for x in settings.ADMINS]
rcpt.append('monitoring_interaction@svobodainfo.org')
send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, rcpt)
