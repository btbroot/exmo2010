"""
This file was generated with the custommenu management command, it contains
the classes for the admin menu, you can customize this class as you want.

To activate your custom menu add the following to your settings.py::
    ADMIN_TOOLS_MENU = 'exmo.menu.CustomMenu'
"""

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from admin_tools.menu import items, Menu


class CustomMenu(Menu):
    """
    Custom Menu for exmo admin site.
    """
    class Media:
        js = (
            'admin_tools/js/jquery/jquery.cookie.min.js',
            'dashboard/js/dashboard-cookie.js',
            )
        css = ()

    def init_with_context(self, context):
        self.children = [
            items.MenuItem(_('Dashboard'), reverse('exmo2010:index')),

        ]
        request = context['request']
        children = [
            items.MenuItem(_('Profile'), reverse('exmo2010:user_profile')),
        ]
        if request.user.is_active:
            children += [
                items.MenuItem(_('Change password'), reverse('exmo2010:password_change')),
                items.MenuItem(_('Log out'), reverse('exmo2010:logout')),
            ]
            if request.user.get_full_name():
                welcome_msg = request.user.get_full_name()
            else:
                welcome_msg = request.user.username
        else:
            children += [
                items.MenuItem(_('Log in'), reverse('exmo2010:login')),
            ]
            welcome_msg = "Anonymous"
        msg = _('Welcome,') + ' ' + welcome_msg
        self.children.append(items.MenuItem(msg, children = children))
