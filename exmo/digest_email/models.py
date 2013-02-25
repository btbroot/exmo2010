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
Digest email models module
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta



class Digest(models.Model):
    "Список дайджестов"

    name    = models.CharField(max_length = 255, verbose_name=_('name'), unique = True)
    "Наименование"

    def __unicode__(self):
        return self.name

    def get_last(self, user):
        journal = DigestJournal.objects.filter(user = user, digest = self)
        if journal:
            return journal[0].date
        else:
            try:
                pref = DigestPreference.objects.get(user = user, digest = self)
                interval = pref.interval
            except DigestPreference.DoesNotExist:
                interval = 30
            return datetime.now() - timedelta(days = interval)



class DigestJournal(models.Model):
    "Журнал учета отсылки дайджеста"

    user = models.ForeignKey(User)
    "Кому отправили"

    date = models.DateTimeField(auto_now = True, verbose_name = _('send date'))
    "Когда отправили. Дата изменяется каждый раз при сохранении"

    digest = models.ForeignKey(Digest, verbose_name = _('digest'))
    "Что за дайджест отправили"

    def __unicode__(self):
        return _("%(date)s: %(digest)s for %(user)s") % {'digest': self.digest, 'user': self.user, 'date': self.date}

    class Meta:
        ordering = (
            '-date',
        )



class DigestPreference(models.Model):
    "Настройки дайджестов"

    user = models.ForeignKey(User, verbose_name = _('user'))
    "Пользователь"

    digest = models.ForeignKey(Digest, verbose_name = _('digest'))
    "Дайджест"

    interval = models.PositiveIntegerField(default = 1, verbose_name = _('interval (hours)'))
    "Периодичность дайджестов в часах"

    def __unicode__(self):
        return _("%(digest)s for %(user)s") % {'digest': self.digest, 'user': self.user}

    class Meta:
        unique_together = (
            ('user','digest'),
        )

    def clean(self):
        if self.interval < 1:
            raise ValidationError(_('Digest interval must be more than 1'))
