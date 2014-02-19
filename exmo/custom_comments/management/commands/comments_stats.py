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
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.utils.encoding import smart_str
from livesettings import config_value

from core.tasks import send_email
from custom_comments.utils import comment_report
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

            report = comment_report(monitoring)
            report.update({'site': 'http://' + Site.objects.get_current().domain})

            subject = "Comment report from %(start_date)s to %(end_date)s for %(monitoring_name)s" % {
                'start_date': report.get('start_date'),
                'end_date': report.get('end_date'),
                'monitoring_name': report.get('monitoring_name'),
            }

            rcpt = [x[1] for x in settings.ADMINS]
            rcpt.append(config_value('EmailServer', 'NOTIFY_LIST_REPORT'))

            send_email.delay(rcpt, subject, 'comments_stats', context=report)
