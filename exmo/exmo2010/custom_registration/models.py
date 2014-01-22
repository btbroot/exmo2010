# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.template import loader, Context
from django.utils.translation import ugettext as _
from livesettings import config_value
from registration.models import RegistrationProfile


class CustomRegistrationProfile(RegistrationProfile):

    class Meta:
        proxy = True

    def send_activation_email(self, site):
        """
        Send activation email.

        """
        protocol = 'http'
        subject = _('Registration on ') + unicode(site)
        from_email = config_value('EmailServer', 'DEFAULT_FROM_EMAIL')
        activation_url = "%s://%s%s" % (protocol, site, reverse('exmo2010:registration_activate', args=[self.activation_key]))
        login_url = "%s://%s%s" % (protocol, site, settings.LOGIN_URL)

        context = {
            'activation_url': activation_url,
            'login_url': login_url,
            'site': site,
            'subject': subject,
        }

        t_txt = loader.get_template('registration/activation_email.txt')
        t_html = loader.get_template('registration/activation_email.html')
        c = Context(context)

        msg = EmailMultiAlternatives(
            subject,
            t_txt.render(c),
            from_email,
            [self.user.email],
        )
        msg.attach_alternative(t_html.render(c), "text/html")
        msg.send()
