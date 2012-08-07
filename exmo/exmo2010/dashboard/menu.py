"""
This file was generated with the custommenu management command, it contains
the classes for the admin menu, you can customize this class as you want.

To activate your custom menu add the following to your settings.py::
    ADMIN_TOOLS_MENU = 'exmo.menu.CustomMenu'
"""

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

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
        children = [
            items.MenuItem(_('Profile'), reverse('exmo2010:user_profile')),
        ]
        if request.user.is_active:
            children += [
                items.MenuItem(_('Change password'), reverse('auth_password_change')),
                items.MenuItem(_('Log out'), reverse('auth_logout')),
            ]
            if request.user.get_full_name():
                welcome_msg = request.user.get_full_name()
            else:
                welcome_msg = request.user.username
        else:
            children += [
#                items.MenuItem(_('Register'), reverse('registration_register')),
                items.MenuItem(_('Log in'), reverse('auth_login')),
            ]
            welcome_msg = "Anonymous"
        msg = _('Welcome,') + ' ' + welcome_msg
        self.children.append(items.MenuItem(msg, children = children))

        rep_children = [
            items.MenuItem(_('Gender stats'), reverse('exmo2010:gender_stats')),
            ]
        self.children.append(items.MenuItem(_('Reports'), children=rep_children))

        communication_children = []

        for key, value in COMMUNICATION_REPORT_TYPE_DICT.iteritems():
            communication_children.append(
                items.MenuItem(
                    value, reverse('exmo2010:comment_list', args=[key,])
                )
            )

        if request.user.is_active and request.user.profile.is_expert:
            self.children.append(items.MenuItem(_('Communication'), children=communication_children))
