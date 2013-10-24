# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Foundation "Institute for Information Freedom Development"
# Copyright 2013 Al Nikolov
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
from datetime import datetime, timedelta

from celery.task import periodic_task
from celery.task.schedules import crontab
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.utils.translation import ugettext as _
from livesettings import config_value

from core.helpers import use_locale
from core.tasks import send_email
from exmo2010.models import Score, UserProfile


@periodic_task(run_every=crontab(minute="*/60"))
@use_locale
def send_digest(timestamp=datetime.now()):
    """
    Send digest.

    """
    users = User.objects.filter(userprofile__notification_type=UserProfile.NOTIFICATION_DIGEST,
                                is_active=True,
                                email__isnull=False)\
                        .exclude(email__exact='')

    current_site = Site.objects.get_current()
    expert = config_value('GlobalParameters', 'EXPERT')
    subject = _("%(prefix)s Email digest") % {
        'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
    }
    for user in users:
        profile = user.userprofile
        last_date = profile.digest_date_journal
        if not last_date:
            last_date = datetime.now() - timedelta(days=profile.notification_interval)
        interval = profile.notification_interval
        if timestamp - last_date < timedelta(hours=interval):
            continue

        if profile.is_expertA or profile.is_manager_expertB:
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
        context = {
            'comments': comments,
            'expert': expert,
            'from': last_date,
            'site': current_site,
            'till': timestamp,
            'user': user,
        }

        send_email.delay(user.email, subject, 'digest', context=context)

        profile.digest_date_journal = datetime.now()
        profile.save()
