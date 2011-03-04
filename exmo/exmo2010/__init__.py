# This file is part of EXMO2010 software.
# Copyright 2010-2011, 2011 Al Nikolov
# Copyright 2010-2011, 2011 Institute for Information Freedom Development
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

from django.contrib.comments.signals import comment_will_be_posted
from django.contrib.auth.models import User
from exmo.exmo2010.models import Score
from exmo.exmo2010.signals import claim_was_posted
from exmo.exmo2010.helpers import comment_notification
from exmo.exmo2010.helpers import claim_notification
from exmo.exmo2010.helpers import post_save_model
from exmo.exmo2010.helpers import create_profile
from exmo.exmo2010.helpers import score_change_notify
from django.db.models.signals import post_save



from django.conf import settings
if settings.USE_EMAIL:
    comment_will_be_posted.connect(comment_notification)
    claim_was_posted.connect(claim_notification)
    post_save.connect(score_change_notify, sender=Score)

post_save.connect(post_save_model)
post_save.connect(create_profile, sender=User)
