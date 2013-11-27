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
import os
from email.mime.image import MIMEImage

from celery.task import task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.mail.utils import DNS_NAME
from django.template import loader, Context
from livesettings import config_value

from core.helpers import use_locale


@task(default_retry_delay=settings.EMAIL_DEFAULT_RETRY_DELAY,
      max_retries=settings.EMAIL_MAX_RETRIES,
      rate_limit=settings.EMAIL_RATE_LIMIT)
@use_locale
def send_email(recipients, subject, template_name, **kwargs):
    """
    Generic function for sending emails.

    """
    attachments = kwargs.get("attachments", {})
    context = kwargs.get("context", {})
    mdn = kwargs.get("mdn", {})

    if not isinstance(recipients, (tuple, list)):
        recipients = [recipients, ]

    t_txt = loader.get_template('.'.join([template_name, 'txt']))
    t_html = loader.get_template('.'.join([template_name, 'html']))

    c = Context(context)

    message_txt = t_txt.render(c)
    message_html = t_html.render(c)

    from_email = config_value('EmailServer', 'DEFAULT_FROM_EMAIL')

    task_id = send_email.request.id

    if mdn:
        headers = {
            'Disposition-Notification-To': from_email,
            'X-Confirm-Reading-To': from_email,
            'Return-Receipt-To': from_email,
            'Message-ID': '<%s@%s>' % (task_id, DNS_NAME),
        }
    else:
        headers = {}

    msg = EmailMultiAlternatives(
        subject,
        message_txt,
        from_email,
        recipients,
        headers=headers
    )
    msg.attach_alternative(message_html, "text/html")

    for cid in attachments:
        try:
            fp = open(os.path.join(settings.STATIC_ROOT, attachments[cid]), 'rb')
        except:
            continue
        msgImage = MIMEImage(fp.read())
        fp.close()

        msgImage.add_header('Content-ID', '<%s>' % cid)
        msgImage.add_header('Content-Disposition', 'inline')

        msg.attach(msgImage)

    msg.send()
