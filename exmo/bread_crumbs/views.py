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
from django.core.urlresolvers import reverse
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _

from exmo2010.models import Monitoring, Score, Task


class BreadcrumbsView(TemplateView):

    def get(self, request, *args, **kwargs):
        crumbs = ['Home']
        breadcrumbs(request, crumbs)
        return super(BreadcrumbsView, self).get(request, *args, **kwargs)


def breadcrumbs(request, items, obj=None):
    """Breadcrumbs. Common view for all pages
    IN: request, string list of crumbs and model object if necessary
    OUT: modified request

    """
    crumbs = {
        'Home': ('', reverse('exmo2010:index')),
        'Monitoring': (_('Monitoring cycles'), reverse('exmo2010:monitoring_list')),
        'Ratings': (_('Ratings'), reverse('exmo2010:ratings')),
    }

    try:
        expert = request.user.profile.is_expert
    except:
        expert = False

    if isinstance(obj, Score):
        crumbs['ScoreView'] = (
            _('Parameter'),
            reverse('exmo2010:score_view',
                    args=[obj.pk])
        )
        obj = obj.task

    if isinstance(obj, Task):
        crumbs['TasksMonitoringOrganization'] = (
            obj.organization.name,
            reverse('exmo2010:tasks_by_monitoring_and_organization',
                    args=[obj.organization.monitoring.pk, obj.organization.pk])
        )
        crumbs['ScoreList'] = (
            _('Organization'),
            reverse('exmo2010:score_list_by_task',
                    args=[obj.pk])
        )
        obj = obj.organization.monitoring

    if isinstance(obj, Monitoring):
        crumbs['TasksMonitoring'] = (
            _('Task for monitoring ') + obj.name,
            reverse('exmo2010:tasks_by_monitoring',
                    args=[obj.pk])
        )

    if obj:
        if expert:
            crumbs['Organization'] = (
                _('Monitoring cycle'),
                reverse('exmo2010:tasks_by_monitoring',
                        args=[obj.pk])
            )
        else:
            if obj.status == 5:
                crumbs['Organization'] = (
                    _('Rating'),
                    reverse('exmo2010:monitoring_rating',
                            args=[obj.pk])
                )
            else:
                crumbs['Organization'] = (
                    _('Tasks'),
                    reverse('exmo2010:tasks_by_monitoring',
                            args=[obj.pk])
                )

    for item in items:
        request.breadcrumbs((crumbs[item],))

    request.expert = expert
