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

import datetime

from django.db import models
from django.utils.translation import ugettext as _

from core.utils import clean_message
from .base import BaseModel


class Clarification(BaseModel):
    """
    Модель уточнений, по наличию даты закрытия определяется
    закрыто уточнение или нет.
    """
    score = models.ForeignKey("Score", verbose_name=_('score'))

    comment = models.TextField(blank=True, verbose_name=_('comment'))
    open_date = models.DateTimeField(auto_now_add=True, verbose_name=_('clarification open'))
    close_date = models.DateTimeField(null=True, blank=True, verbose_name=_('clarification close'))
    creator = models.ForeignKey("auth.User",
                                verbose_name=_('creator'),
                                related_name='clarification_creator')

    answer = models.TextField(blank=True, verbose_name=_('comment'))

    close_user = models.ForeignKey("auth.User",
                                   null=True,
                                   blank=True,
                                   verbose_name=_('user who close'),
                                   related_name='clarification_close_user')

    def add_answer(self, user, answer):
        self.answer = clean_message(answer)
        self.close_user = user
        self.close_date = datetime.datetime.now()
        self.save()
        return self

    def __unicode__(self):
        return _('clarification for %(score)s from %(creator)s') % self.__dict__

    class Meta(BaseModel.Meta):
        permissions = (("view_clarification", "Can view clarification"),)

    @property
    def addressee(self):
        return self.score.task.user
