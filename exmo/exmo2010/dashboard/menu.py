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
This file was generated with the custommenu management command, it contains
the classes for the admin menu, you can customize this class as you want.

To activate your custom menu add the following to your settings.py::
    ADMIN_TOOLS_MENU = 'exmo.menu.CustomMenu'
"""

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from admin_tools.menu import items, Menu
from exmo2010.models import Task


class CustomMenu(Menu):
    """
    Custom Menu for exmo admin site.
    """
    template = 'user_dashboard/menu.html'

    class Media:
        js = (
            'admin_tools/js/jquery/jquery.cookie.min.js',
        )
        css = (
            'dashboard/css/menu.css',
        )

    def init_with_context(self, context):
        self.children = [
            items.MenuItem(_('Dashboard'), reverse('exmo2010:index')),
        ]
        request = context['request']

        if request.user.is_superuser:
            self.children.append(items.MenuItem(_('Admin'),
                                                reverse('admin:index')))

        if request.user.is_authenticated() and request.user.profile.is_organization:
            task_id = request.user.profile.get_task_review_id()
            if task_id is not None:
                self.children += [
                    items.MenuItem(_('Scores of my organisation'),
                                   reverse('exmo2010:score_list_by_task',
                                           args=[task_id])),
                    ]

        if request.user.is_active and request.user.profile.is_expertB \
            and not request.user.profile.is_expertA:
            communication_children = [
                items.MenuItem(_('Comments'),
                               reverse('exmo2010:comment_list')),
                items.MenuItem(_('Clarifications'),
                               reverse('exmo2010:clarification_list')),
                items.MenuItem(_('Claims'),
                               reverse('exmo2010:claim_list'))
            ]
            self.children.append(items.MenuItem(_('Messages'),
                                                children=communication_children))

        self.children.append(items.MenuItem(_('Ratings'),
                                            reverse('exmo2010:ratings')))

        self.children.append(items.MenuItem(_('Statistics'),
                                            reverse('exmo2010:monitoring_report')))

        self.children.append(items.MenuItem(_('Help'),
                                            reverse('exmo2010:help')))

