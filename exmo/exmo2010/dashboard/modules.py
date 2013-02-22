# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012, 2013 Institute for Information Freedom Development
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

from admin_tools.dashboard.modules import DashboardModule
from django.utils.translation import ugettext_lazy as _

class ObjectList(DashboardModule):
    """
    A module that displays a list of links.
    As well as the :class:`~admin_tools.dashboard.modules.DashboardModule`
    properties, the :class:`~admin_tools.dashboard.modules.ObjectList` takes
    an extra keyword argument:

    ``layout``
        The layout of the list, possible values are ``stacked`` and ``inline``.
        The default value is ``stacked``.

    Link list modules children are simple python dictionaries that can have the
    following keys:

    ``title``
        The link title.

    ``object_list``
        The link URL.

    Children can also be iterables (lists or tuples) of length 2, 3 or 4.

    Here's a small example of building a link list module::

        from admin_tools.dashboard import modules, Dashboard

        class MyDashboard(Dashboard):
            def __init__(self, **kwargs):
                Dashboard.__init__(self, **kwargs)

                self.children.append(modules.LinkList(
                    layout='inline',
                    children=(
                        {
                            'title': 'MyModel objects',
                            'object_list': MyModel.objects.all(),
                        },
                    )
                ))

    """

    title = _('List')
    template = 'user_dashboard/modules/object_list.html'
    layout = 'stacked'

    def init_with_context(self, context):
        if self._initialized:
            return
        new_children = []
        for link in self.children:
            if isinstance(link, (tuple, list,)):
                link_dict = {'title': link[0], 'object_list': link[1]}
                new_children.append(link_dict)
            else:
                new_children.append(link)
        self.children = new_children
        self._initialized = True
