# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013 Foundation "Institute for Information Freedom Development"
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
from celery.task import periodic_task
from celery.task.schedules import crontab

from digest_email.digest import CommentDigest, ScoreDigest
from digest_email.models import Digest


@periodic_task(run_every=crontab(minute="*/60"))
def comment_notification():
    """
    Task for sending comment digest.

    """

    digest = CommentDigest(Digest.objects.get(name='notify_comment'))
    digest.send()


@periodic_task(run_every=crontab(minute="*/60"))
def score_notification():
    """
    Task for sending score digest.

    """
    digest = ScoreDigest(Digest.objects.get(name='notify_score'))
    digest.send()
