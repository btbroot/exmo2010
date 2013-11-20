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

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

from core.utils import clean_message
from .base import BaseModel


class Claim(BaseModel):
    """Модель претензий/замечаний"""

    score = models.ForeignKey("exmo2010.Score", verbose_name=_('score'))
    comment = models.TextField(blank=True, verbose_name=_('comment'))
    open_date = models.DateTimeField(auto_now_add=True, verbose_name=_('claim open'))
    # Дата закрытия. По её наличию определяется закрыта претензия или нет.
    close_date = models.DateTimeField(null=True, blank=True, verbose_name=_('claim close'))

    # Ответ.
    answer = models.TextField(blank=True, verbose_name=_('comment'))

    # Кто закрыл претензию.
    close_user = models.ForeignKey(User, null=True, blank=True,
        verbose_name=_('user who close'), related_name='close_user')

    creator = models.ForeignKey(User, verbose_name=_('creator'), related_name='creator')
    addressee = models.ForeignKey(User, default=1, verbose_name=_('addressee'), related_name='addressee')

    def add_answer(self, user, answer):
        self.answer = clean_message(answer)
        self.close_user = user
        self.close_date = datetime.datetime.now()
        self.save()
        return self

    def __unicode__(self):
        return _('claim for %(score)s from %(creator)s') % self.__dict__

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для того, чтобы автоматически заполнять
        значение поля`addressee`, но только в момент первоначального создания
        экземпляра модели.
        """
        if not self.id:  # Экземпляр новый.
            self.addressee = self.score.task.user
        super(Claim, self).save(*args, **kwargs)

    class Meta(BaseModel.Meta):
        permissions = (("view_claim", "Can view claim"),)
