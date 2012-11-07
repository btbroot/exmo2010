# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
from django.contrib.auth.models import User
from django.contrib.comments.signals import comment_will_be_posted
from django.contrib.comments.signals import comment_was_posted
from exmo2010 import signals
from exmo2010.helpers import comment_notification
from exmo2010.helpers import comment_change_status
from exmo2010.helpers import claim_notification
from exmo2010.helpers import post_save_model
from exmo2010.helpers import create_profile
from exmo2010.helpers import create_calendar
from exmo2010.helpers import create_revision
from exmo2010.helpers import score_change_notify
from exmo2010.models import Score
from exmo2010.models import Monitoring
from exmo2010.sites import site


if hasattr(settings,'USE_EMAIL') and settings.USE_EMAIL:
    comment_will_be_posted.connect(comment_notification)
    signals.claim_was_posted.connect(claim_notification)
    signals.score_was_changed.connect(score_change_notify)

post_save.connect(post_save_model)
#post_save.connect(create_profile, sender=User)
post_save.connect(create_calendar, sender=Monitoring)
pre_save.connect(create_revision, sender=Score)

# Регистрация хэндлера для сигнала перед отправкой комментария,
# хэндлер изменяет статус комментариев.
comment_was_posted.connect(comment_change_status)

