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
from django.contrib.sites import models as sitesModel
from exmo2010.models import Monitoring
from exmo2010.helpers import comment_report

m_pk = sys.argv[1]
monitoring = Monitoring.objects.get(pk=m_pk)

start_date = monitoring.interact_date

limit = time_to_answer = monitoring.time_to_answer

report = comment_report(monitoring)

end_date = report.get('end_date')
comments_without_reply = report.get('comments_without_reply')
fail_comments_without_reply = report.get('fail_comments_without_reply')
fail_soon_comments_without_reply = report.get('fail_soon_comments_without_reply')
fail_comments_with_reply = report.get('fail_comments_with_reply')
comments_with_reply = report.get('comments_with_reply')
org_comments = report.get('org_comments')
iifd_all_comments = report.get('iifd_all_comments')
active_organization_stats = report.get('active_organization_stats')
total_org = report.get('total_org')
reg_org = report.get('reg_org')
active_iifd_person_stats = report.get('active_iifd_person_stats')

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
