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
from exmo.exmo2010 import models as exmoModel
from datetime import datetime, timedelta
from django.db.models import Q

start_date = datetime(2011,05,19)
end_date = datetime.now()
limit = 4

#get all comments from org
org_comments = commentModel.Comment.objects.filter(
    content_type__model = 'score',
    submit_date__gte = start_date,
    object_pk__in = exmoModel.Score.objects.filter(task__monitoring__pk__in = [11,]),
    user__in = authModel.User.objects.filter(groups__name = 'organizations')).order_by('submit_date')

comments_without_reply = []
fail_comments_without_reply = []
comments_with_reply = []
fail_soon_comments_with_reply = []
fail_comments_with_reply = []

for org_comment in org_comments:
    iifd_comments = commentModel.Comment.objects.filter(
        content_type__model = 'score',
        submit_date__gte = org_comment.submit_date,
        object_pk = org_comment.object_pk,
        user__in = authModel.User.objects.filter(Q(groups__name__in = ['experts','expertsA','expertsB']) | Q(is_superuser = True))
    )
    if (not iifd_comments.count() > 0) and (end_date - org_comment.submit_date).days > limit:
        fail_comments_without_reply.append(org_comment)
    elif (not iifd_comments.count() > 0) and (end_date - org_comment.submit_date).days > limit-1:
        fail_soon_comments_without_reply.append(org_comment)
    elif not iifd_comments.count() > 0:
        comments_without_reply.append(org_comment)
    if (iifd_comments.count() > 0) and (end_date - org_comment.submit_date).days > limit:
        fail_comments_with_reply.append(org_comment)
    if (iifd_comments.count() > 0) and (end_date - org_comment.submit_date).days <= limit:
        comments_with_reply.append(org_comment)


from django.template import loader, Context
from django.conf import settings

t = loader.get_template('exmo2010/helpers/score_comments_stat.html')
c = Context({
    'start_date': start_date,
    'end_date': end_date,
    'comments_without_reply': comments_without_reply,
    'fail_comments_without_reply': fail_comments_without_reply,
    'fail_comments_with_reply': fail_comments_with_reply,
    'fail_soon_comments_with_reply': fail_soon_comments_with_reply,
    'comments_with_reply': comments_with_reply,
    'org_comments_count': org_comments.count(),
    'limit': limit,
    'site': sitesModel.Site.objects.get(name = 'exmo.svobodainfo.org'),
    })

message = t.render(c)
from django.core.mail import send_mail

subject = "Comment report from %(start_date)s to %(end_date)s" % { 'start_date': start_date, 'end_date': end_date }

rcpt = [ x[1] for x in settings.ADMINS]
rcpt.append('monitoring-list@svobodainfo.org')
send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, rcpt)
