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
