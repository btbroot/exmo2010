# -*- coding: utf-8 -*-
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
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils.translation import ugettext as _
from livesettings import config_value

from core.tasks import send_email
from exmo2010.models import UserProfile, MONITORING_INTERACTION, MONITORING_FINALIZING


def comment_notification(sender, **kwargs):
    """
    Comments notification.

    """
    comment = kwargs['comment']
    score = comment.content_object
    monitoring = score.task.organization.monitoring
    if not monitoring.status in [MONITORING_INTERACTION, MONITORING_FINALIZING]:
        return
    request = kwargs['request']
    user = comment.user

    # Update user.email
    if not user.email and comment.user_email:
        user.email = comment.user_email
        user.save()

    # get emails by superusers, experts A and experts B:
    experts_emails = User.objects.filter(Q(is_superuser=True, email__isnull=False) |
                                         Q(groups__name=UserProfile.expertA_group) |
                                         Q(pk=score.task.user.pk),
                                         is_active=True,
                                         email__isnull=False,
                                         userprofile__notification_type=UserProfile.NOTIFICATION_ONEBYONE)\
                                 .exclude(Q(pk=comment.user.pk, userprofile__notification_self=False) |
                                          Q(email__exact=''))\
                                 .values('email')\
                                 .distinct()

    # whole comment thread
    experts_thread = experts_emails.filter(userprofile__notification_thread=True)
    # last comment
    experts_one = experts_emails.filter(userprofile__notification_thread=False)

    # get emails by organizations representatives:
    orgs_emails = User.objects.filter(userprofile__organization=score.task.organization,
                                      is_active=True,
                                      email__isnull=False,
                                      userprofile__notification_type=UserProfile.NOTIFICATION_ONEBYONE)\
                              .exclude(Q(pk=comment.user.pk, userprofile__notification_self=False) |
                                       Q(email__exact=''))\
                              .values('email')\
                              .distinct()

    # whole comment thread
    orgs_thread = orgs_emails.filter(userprofile__notification_thread=True)
    # last comment
    orgs_one = orgs_emails.filter(userprofile__notification_thread=False)

    subject = u'%(prefix)s%(monitoring)s - %(org)s: %(code)s' % {
        'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
        'monitoring': monitoring,
        'org': score.task.organization.name.split(':')[0],
        'code': score.parameter.code,
    }
    title = '%s: %s' % (score.task.organization, score.parameter)
    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http',
                         request.get_host(),
                         reverse('exmo2010:score_view',
                         args=[score.pk]))

    context = {
        'title': title,
        'url': url,
    }

    thread = sender.objects.filter(object_pk=comment.object_pk)

    # send notifications with the last comment:
    _send_mails(experts_one, subject, context, [comment], True)
    _send_mails(orgs_one, subject, context, [comment])

    # send notifications with whole comment thread:
    _send_mails(experts_thread, subject, context, thread, True)
    _send_mails(orgs_thread, subject, context, thread)


def _send_mails(rcpts, subject, context, comments, is_experts=False):
    """
    Sending comments notification mails.

    """
    expert = _(config_value('GlobalParameters', 'EXPERT'))
    for comment in comments:
        if not comment.user_is_expert():
            legal_user_name = comment.user_legal_name()
        else:
            legal_user_name = comment.user_legal_name() if is_experts else expert

        setattr(comment, 'legal_user_name', legal_user_name)

    context['comments'] = comments

    for rcpt in rcpts:
        email = ''.join(rcpt['email'].split())
        send_email.delay(email, subject, 'score_comment', context=context)
