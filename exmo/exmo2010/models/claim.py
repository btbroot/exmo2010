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
import datetime

from ckeditor.fields import RichTextField
from django.contrib.auth.models import User
from django.db import models
from django.forms.models import modelform_factory
from django.utils.translation import ugettext_lazy as _

from core.utils import clean_message
from .base import BaseModel


class Claim(BaseModel):
    """Модель претензий/замечаний"""

    class Meta(BaseModel.Meta):
        permissions = (("view_claim", "Can view claim"),)

    score = models.ForeignKey("exmo2010.Score", verbose_name=_('score'))
    comment = RichTextField(blank=True, verbose_name=_('comment'), config_name='simplified')
    open_date = models.DateTimeField(auto_now_add=True, verbose_name=_('claim open'))
    # Дата закрытия. По её наличию определяется закрыта претензия или нет.
    close_date = models.DateTimeField(null=True, blank=True, verbose_name=_('claim close'))

    answer = RichTextField(blank=True, verbose_name=_('answer'), config_name='simplified')

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

    def answer_form(self, data=None):
        AnswerForm = modelform_factory(Claim, fields=['answer'])
        return AnswerForm(data=data, prefix='answer_claim_%s' % self.pk)

    @staticmethod
    def form(data=None):
        Form = modelform_factory(Claim, fields=['comment'])
        return Form(data=data, prefix='claim')

    def __unicode__(self):
        return _('claim for {obj.score} from {obj.creator}').format(obj=self)

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save для того, чтобы автоматически заполнять
        значение поля`addressee`, но только в момент первоначального создания
        экземпляра модели.
        """
        if not self.id:  # Экземпляр новый.
            self.addressee = self.score.task.user
        super(Claim, self).save(*args, **kwargs)

