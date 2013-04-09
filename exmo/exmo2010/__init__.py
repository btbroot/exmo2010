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
from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.conf import settings
from django.contrib.comments.signals import comment_will_be_posted
from django.contrib.comments.signals import comment_was_posted

from exmo2010.helpers import *
from exmo2010.models import Monitoring, Score
from exmo2010.signals import *
from exmo2010.view.helpers import create_revision, score_change_notify
from tasks.views import task_user_change_notify


if hasattr(settings, 'USE_EMAIL') and settings.USE_EMAIL:
    comment_will_be_posted.connect(comment_notification)
    score_was_changed.connect(score_change_notify)
    claim_was_posted_or_deleted.connect(claim_notification)
    clarification_was_posted.connect(clarification_notification)
    task_user_changed.connect(task_user_change_notify)

post_save.connect(post_save_model)
pre_save.connect(create_revision, sender=Score)

# Регистрация хэндлера для сигнала перед отправкой комментария,
# хэндлер изменяет статус комментариев.
comment_was_posted.connect(comment_change_status)
