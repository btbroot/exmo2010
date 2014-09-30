# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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
from django import forms
from django.utils.translation import ugettext_lazy as _
from livesettings import config_register, config_register_list
from livesettings.values import *


class StringValueWidget(StringValue):
    """
    Custom class which provides text input form with style.

    """
    class field(StringValue.field):
        def __init__(self, *args, **kwargs):
            kwargs['widget'] = forms.TextInput(attrs={'style': 'width: 250px'})
            super(StringValueWidget.field, self).__init__(*args, **kwargs)


# setup a group to hold all our possible Emails configs
EMAIL_GROUP = ConfigurationGroup('EmailServer', _('Email Server Settings'), ordering=0)

config_register_list(
    StringValueWidget(
        EMAIL_GROUP,
        'DEFAULT_FROM_EMAIL',
        description=_('Email'),
        ordering=0,
        default='exmo@svobodainfo.org',
        help_text=_('Default email address'),
    ),

    StringValueWidget(
        EMAIL_GROUP,
        'EMAIL_SUBJECT_PREFIX',
        description=_('Prefix'),
        ordering=1,
        default='[exmo] ',
        help_text=_('Email subject prefix'),
    ),

    StringValueWidget(
        EMAIL_GROUP,
        'DEFAULT_SUPPORT_EMAIL',
        description=_('Email'),
        ordering=2,
        default='tsupport@svobodainfo.org',
        help_text=_('Default support email address'),
    ),

    StringValueWidget(
        EMAIL_GROUP,
        'NOTIFY_LIST_REPORT',
        description=_('Email'),
        ordering=3,
        default='monitoring-report@svobodainfo.org',
        help_text=_('Notify list report'),
    ),

    StringValueWidget(
        EMAIL_GROUP,
        'CERTIFICATE_ORDER_NOTIFICATION_EMAIL',
        description=_('Email'),
        ordering=4,
        default='tsupport@svobodainfo.org',
        help_text=_('Certificate order notification email'),
    ),
)

LINKS_GROUP = ConfigurationGroup('Links', _('Links'), ordering=1)

config_register_list(
    StringValueWidget(
        LINKS_GROUP,
        'LINK_TO_PORTAL',
        description=_('Link'),
        ordering=0,
        default='http://infometer.org/',
        help_text=_('Link to portal'),
    ),
    StringValueWidget(
        LINKS_GROUP,
        'LINK_TO_METHODOLOGY',
        description=_('Link'),
        ordering=0,
        default='http://infometer.org/monitoring/metodika/',
        help_text=_('Link to methodology'),
    ),
)

GLOBAL_PARAMETERS_GROUP = ConfigurationGroup('GlobalParameters', _('Global Parameters'), ordering=2)

config_register_list(
    StringValueWidget(
        GLOBAL_PARAMETERS_GROUP,
        'EXPERT',
        description=_('Expert'),
        ordering=0,
        default=_('Freedom Information Foundation Expert'),
        help_text=_('Default organization`s expert'),
    ),
    StringValueWidget(
        GLOBAL_PARAMETERS_GROUP,
        'OG:DESCRIPTION',
        description=_('og:description meta tag content'),
        ordering=0,
        default='',
        help_text=_('og:description meta tag content'),
    ),
)
