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

from digest_email.models import DigestJournal
from digest_email.models import Digest
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.core.mail import EmailMessage
from django.template import loader, Context
from django.conf import settings
from django.utils.translation import ugettext as _



class DigestSend(object):
    "Класс для отсылки дайджестов"

    digest = None
    users = None
    digest_template = "digest_email/digest.html"
    element_template = ""

    def __init__(self, digest):
        "Принимает наименование дайджеста"
        self.digest = digest
        #get all users for digest
        self.users = User.objects.filter(digestpreference__digest = self.digest, email__isnull = False).exclude(email__exact='').distinct('email')
        self.element_template = "digest_email/%s.html" % self.digest.name.replace(' ','_')

    def get_content(self, user, timestamp = datetime.now()):
        "Метод для формирования queryset объектов для отсылки"
        raise NotImplementedError

    def render(self, queryset, context, extra_context = {}):
        """Метод для формирования сообщения по шаблону и контексту. Принимает extra_context
           для передачи доп. контекста в шаблонизатор.
        """
        t = loader.get_template(self.digest_template)
        c = Context({
            'object_list': queryset,
            'element_template': self.element_template,
            'digest': self.digest,
        })
        if context: c.update(context)
        if extra_context: c.update(extra_context)
        return t.render(c)

    def send(self, timestamp = datetime.now(), send = True, headers = {}, extra_context = {}):
        """Метод для отправки дайджеста. Для всех пользователей вызывается self.get_content,
           результат отдается в self.render (можно использовать extra_context), после чего письмо отправляется.
        """
        for user in self.users:
            digest_pref = user.digestpreference_set.get(digest = self.digest)
            if timestamp - self.digest.get_last(user) < timedelta(hours=digest_pref.interval):
                continue
            qs = self.get_content(user, timestamp)
            if not qs:
                continue
            subject = _("%(prefix)sEmail digest for %(digest)s") % {
                'prefix': settings.EMAIL_SUBJECT_PREFIX,
                'digest': self.digest,
            }
            context = {
                'user': user,
                'from': self.digest.get_last(user),
                'till': timestamp,
            }
            email = EmailMessage(subject, self.render(qs, context, extra_context = {}), settings.DEFAULT_FROM_EMAIL, [user.email,], [], headers = headers)
            if send:
                email.send()
                journal = DigestJournal(user = user, digest = self.digest)
                journal.save()
