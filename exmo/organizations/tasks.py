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
import imaplib
import re
import sys

from celery.task import periodic_task
from celery.task.schedules import crontab
from django.conf import settings

from exmo2010.models import EmailTasks, Organization, Score


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
                    match = re.search("Original-Message-ID: <(?P<task>[\w\d.-]+)@(?P<host>[\w\d.-]+)>", email_body)

                    if match:
                        task_id = match.group('task')

                        task = EmailTasks.objects.get(task_id=task_id)
                        m.store(email_id, '+FLAGS', '\\Deleted')  # add 'delete' flag
                        org = Organization.objects.get(pk=task.organization_id)
                        if org.inv_status in ['SNT', 'NTS']:
                            org.inv_status = 'RD'
                            org.save()
            except:
                continue
        m.expunge()


@periodic_task(run_every=crontab(minute="*/30"))
def change_inv_status():
    """
    Check all organizations with 'registrated' invitation status for activity.

    """
    orgs = Organization.objects.filter(inv_status='RGS')
    for org in orgs:
        scores = Score.objects.filter(task__organization=org)
        is_active = org.userprofile_set.filter(user__comment_comments__object_pk__in=scores).exists()
        if is_active:
            org.inv_status = 'ACT'
            org.save()
