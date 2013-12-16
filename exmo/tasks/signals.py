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
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.template import loader, Context
from django.utils.translation import ugettext as _

from livesettings import config_value


def task_assign_user_notify(sender, **kwargs):
    """
    Notifies assigned expert about her new task
    Receiver of signal, where sender is a Task instance
    """
    task = sender
    email = task.user.email
    if not email:
        return
    subject = _('You have an assigned task')
    if Site._meta.installed:
        site = Site.objects.get_current()
        url = '%s://%s%s' % ('http', site, reverse('exmo2010:score_list_by_task', args=[task.pk]))
    else:
        url = None

    t = loader.get_template('task_user_assigned.html')
    c = Context({'task': task, 'url': url, 'subject': subject})
    message = t.render(c)

    email = EmailMessage(subject, message, config_value('EmailServer', 'DEFAULT_FROM_EMAIL'), [email])
    email.encoding = "utf-8"
    email.content_subtype = "html"
    email.send()

