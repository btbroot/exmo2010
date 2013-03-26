# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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

"""
Модуль для переопределения класса отправки дайджестов
"""

from digest_email.digest import DigestSend
from datetime import datetime
from django.contrib.comments.models import Comment
from exmo2010.models import Score

class ScoreCommentDigest(DigestSend):

    def get_content(self, user, timestamp = datetime.now()):
        "Собираем комментарии для отправления с момента последней отправки дайджеста по timestamp"

        if user.userprofile.is_expertA or user.userprofile.is_manager_expertB:
            score_pk = Score.objects.all()
        elif user.userprofile.is_expertB:
            score_pk = Score.objects.filter(task__user = user)
        elif user.userprofile.is_organization:
            score_pk = Score.objects.filter(task__organization__in = user.userprofile.organization.all())
        else:
            score_pk = Score.objects.none()

        last_digest_date = self.digest.get_last(user)
        qs = Comment.objects.filter(
            content_type__model = 'score',
            object_pk__in = score_pk.values_list('id', flat=True),
        ).order_by('submit_date')

        if last_digest_date:
            qs = qs.filter(submit_date__gte = last_digest_date)
        if not user.userprofile.notify_comment_preference['self']:
            qs = qs.exclude(user = user)
        return qs
