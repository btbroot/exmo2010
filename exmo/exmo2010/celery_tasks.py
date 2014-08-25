# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
import imaplib
import re
import sys
from datetime import datetime, timedelta

from celery import shared_task
from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.utils.translation import ugettext as _
from django.utils import translation
from livesettings import config_value

from exmo2010.models import Score, UserProfile, Organization


mail_task_opts = dict(
    default_retry_delay=settings.EMAIL_DEFAULT_RETRY_DELAY,
    max_retries=settings.EMAIL_MAX_RETRIES,
    rate_limit=settings.EMAIL_RATE_LIMIT)


@shared_task(**mail_task_opts)
def send_email(message):
    message.send()


@shared_task(**mail_task_opts)
def send_org_email(message, org_pk):
    message.send()
    Organization.objects.filter(pk=org_pk, inv_status='NTS').update(inv_status='SNT')


@periodic_task(run_every=crontab(minute="*/30"))
def check_mdn_emails():
    """
    Check unseen emails for MDN (Message Disposition Notification).

    """
    try:
        server = settings.IMAP_SERVER
        login = settings.IMAP_LOGIN
        password = settings.IMAP_PASSWORD
        m = imaplib.IMAP4_SSL(server)
        m.login(login, password)
    except:
        print sys.exc_info()[1]
        sys.exit(1)

    m.list()  # list of "folders"
    m.select("INBOX")  # connect to inbox.

    resp, items = m.search(None, "(UNSEEN)")  # check only unseen emails

    if items[0]:
        for email_id in items[0].split():
            try:
                resp, data = m.fetch(email_id, "(RFC822)")  # fetching the mail, "(RFC822)" means "get the whole stuff"
                email_body = data[0][1]  # getting the mail content

                if email_body.find('message/disposition-notification') != -1:
                    # email is MDN
                    match = re.search("Original-Message-ID: <(?P<invitation_code>[\w\d]+)@(?P<host>[\w\d.-]+)>",
                                      email_body)
                    if match:
                        invitation_code = match.group('invitation_code')
                        m.store(email_id, '+FLAGS', '\\Deleted')  # add 'delete' flag
                        org = Organization.objects.get(inv_code=invitation_code)
                        if org.inv_status in ['SNT', 'NTS']:
                            org.inv_status = 'RD'
                            org.save()
            except:
                continue
        m.expunge()


@periodic_task(run_every=crontab(minute="*/60"))
def send_digest(now=datetime.now()):
    from exmo2010.mail import ExmoEmail

    users = User.objects.filter(
        userprofile__notification_type=UserProfile.NOTIFICATION_DIGEST,
        is_active=True,
        email__isnull=False)

    subject = _("%(prefix)s Email digest") % {
        'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
    }
    context = {
        'masked_expert_name': config_value('GlobalParameters', 'EXPERT'),
        'site': Site.objects.get_current(),
    }
    for user in users.exclude(email__exact='').select_related('userprofile'):
        profile = user.userprofile
        last_date = profile.digest_date_journal
        if not last_date:
            last_date = now - timedelta(days=profile.notification_interval)
        interval = profile.notification_interval
        if now - last_date < timedelta(hours=interval):
            continue

        if profile.is_expertA:
            score_pk = Score.objects.all()
        elif profile.is_expertB:
            score_pk = Score.objects.filter(task__user=user)
        elif profile.is_organization:
            score_pk = Score.objects.filter(task__organization__in=profile.organization.all())
        else:
            score_pk = Score.objects.none()

        comments = Comment.objects.filter(
            content_type__model='score',
            object_pk__in=score_pk.values_list('id', flat=True),
        ).order_by('submit_date')

        if last_date:
            comments = comments.filter(submit_date__gte=last_date)
        if not user.userprofile.notification_self:
            comments = comments.exclude(user=user)

        if not comments:
            continue

        context.update({
            'comments': comments,
            'from': last_date,
            'till': now,
            'user': user,
        })

        with translation.override(profile.language or settings.LANGUAGE_CODE):
            message = ExmoEmail(template_basename='mail/digest', context=context, to=[user.email], subject=subject)

        send_email.delay(message)
        profile.digest_date_journal = now
        profile.save()
