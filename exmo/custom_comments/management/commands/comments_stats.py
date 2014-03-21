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
from datetime import date

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.utils.encoding import smart_str
from django.utils import translation
from livesettings import config_value

from custom_comments.utils import comment_report
from exmo2010.celery_tasks import send_email
from exmo2010.mail import ExmoEmail
from exmo2010.models import Monitoring


class Command(BaseCommand):
    """
    Send comments statistics.

    USAGE:
        python manage.py comments_stats monitoring_pk

    """
    help = 'Send comments statistics by monitoring id.'
    args = '<monitoring_pk monitoring_pk ... >'

    def handle(self, *args, **options):
        if not args:
            raise CommandError('Enter monitoring ID in command line!')

        for monitoring_pk in args:
            try:
                monitoring = Monitoring.objects.get(pk=monitoring_pk)
            except Monitoring.DoesNotExist:
                message = smart_str(self.style.ERROR('Monitoring with ID "%s" does not exist!\n' % monitoring_pk))
                self.stderr.write(message)
                continue
            except ValueError:
                message = smart_str(self.style.ERROR('Invalid literal "%s" for monitoring ID!\n' % monitoring_pk))
                self.stderr.write(message)
                continue

            context = comment_report(monitoring)
            context.update({'site': 'http://' + Site.objects.get_current().domain})

            subject = u"Comment report from {monitoring.interact_date} to {today} for {monitoring.name}"
            subject = subject.format(today=date.today(), monitoring=monitoring)

            rcpt = [x[1] for x in settings.ADMINS]
            rcpt.append(config_value('EmailServer', 'NOTIFY_LIST_REPORT'))

            # NOTE: User Story #1900 - Always send comment reports in Russian language.
            with translation.override('ru'):
                send_email.delay(ExmoEmail(template_basename='mail/comments_stats', context=context, to=rcpt, subject=subject))
