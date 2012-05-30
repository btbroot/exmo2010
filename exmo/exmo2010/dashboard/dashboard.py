"""
This file was generated with the customdashboard management command, it
contains the two classes for the main dashboard and app index dashboard.
You can customize these classes as you want.

To activate your index dashboard add the following to your settings.py::
    ADMIN_TOOLS_INDEX_DASHBOARD = 'exmo.dashboard.CustomIndexDashboard'

And to activate the app index dashboard::
    ADMIN_TOOLS_APP_INDEX_DASHBOARD = 'exmo.dashboard.CustomAppIndexDashboard'
"""

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from admin_tools.dashboard import modules, Dashboard, AppIndexDashboard
from admin_tools.utils import get_admin_site_name
from exmo.exmo2010.dashboard import modules as custom_modules
from exmo.exmo2010.view.monitoring import _get_monitoring_list
from exmo.exmo2010 import models as exmo_models

class UserDashboard(Dashboard):
    # we want a 3 columns layout
    columns = 3
    class Media:
        js = ('dashboard/js/jquery.dashboard.js',)
        css = ()

class CustomIndexDashboard(UserDashboard):
    """
    Custom index dashboard for exmo.
    """
    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        # append a link list module for "quick links"
        self.children.append(modules.LinkList(
            _('Quick links'),
            layout='inline',
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                ['holder','holder'],
            ],
            template = "user_dashboard/modules/quicklinks.html",
        ))

        # append another link list module for "support".
        self.children.append(custom_modules.ObjectList(
            _('Monitoring list'),
            children=[
                {
                    'title': None,
                    'object_list': _get_monitoring_list(context['request']),
                },
            ],
            template="user_dashboard/modules/monitoring_list.html",
        ))

        # append a feed module
        self.children.append(modules.Feed(
            _('Svobodainfo news'),
            feed_url='http://www.svobodainfo.org/rss.xml',
            limit=10,
            template = "user_dashboard/modules/feed.html",
        ))
