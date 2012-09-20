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
"""
This file was generated with the custommenu management command, it contains
the classes for the admin menu, you can customize this class as you want.

To activate your custom menu add the following to your settings.py::
    ADMIN_TOOLS_MENU = 'exmo.menu.CustomMenu'
"""

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from exmo2010.models import Task

from admin_tools.menu import items, Menu

from exmo2010.view.reports import COMMUNICATION_REPORT_TYPE_DICT



class CustomMenu(Menu):
    """
    Custom Menu for exmo admin site.
    """
    template = 'user_dashboard/menu.html'

    class Media:
        js = (
            'admin_tools/js/jquery/jquery.cookie.min.js',
            )
        css = ()

    def init_with_context(self, context):
        self.children = [
            items.MenuItem(_('Dashboard'), reverse('exmo2010:index')),
        ]
        request = context['request']
        children = []

        if request.user.is_authenticated():
            if request.user.profile.is_organization:
                task_id = request.user.profile.get_task_review_id()
                if task_id != None:
                    self.children += [
                        items.MenuItem(_('Scores of my organisation'),
                                        reverse('exmo2010:score_list_by_task',
                                        args=[task_id])),
                        ]

        if request.user.is_active:
            children += [
                items.MenuItem(_('Preferences'), reverse('exmo2010:settings')),
                items.MenuItem(_('Log out'), reverse('exmo2010:auth_logout')),
            ]
            if request.user.get_full_name():
                welcome_msg = request.user.get_full_name()
            else:
                welcome_msg = request.user.username
            msg = _('Welcome') + ', ' + welcome_msg
        else:
            children += [
                items.MenuItem(_('Register'), reverse('exmo2010:registration_register')),
                items.MenuItem(_('Log in'), reverse('exmo2010:auth_login')),
            ]
            msg = _('Welcome')
        self.children.append(items.MenuItem(msg, children = children))
        self.children.append(items.MenuItem(_('Ratings'), reverse('exmo2010:ratings')))

        rep_children = []
        if request.user.is_authenticated() and request.user.profile.is_internal():
            rep_children.append(items.MenuItem(_('Gender stats'),
                reverse('exmo2010:gender_stats')))
            rep_children.append(items.MenuItem(_('Monitoring stats'),
                reverse('exmo2010:monitoring_report')))
            self.children.append(items.MenuItem(_('Statistics'), children=rep_children))
        else:
            self.children.append(items.MenuItem(_('Statistics'), reverse('exmo2010:monitoring_report')))
        inf_children = [
            items.MenuItem(_('Help'), reverse('exmo2010:help')),
            items.MenuItem(_('Parameter lists'), "http://www.svobodainfo.org/ru/node/1930"),
            items.MenuItem(_('About project'), reverse('exmo2010:about')),
            ]
        self.children.append(items.MenuItem(_('Information'),
            children=inf_children))

        communication_children = []

        for key, value in COMMUNICATION_REPORT_TYPE_DICT.iteritems():
            communication_children.append(
                items.MenuItem(
                    value, reverse('exmo2010:comment_list', args=[key,])
                )
            )

        if request.user.is_active and request.user.profile.is_expert:
            self.children.append(items.MenuItem(_('Communication'), children=communication_children))
