# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013 Foundation "Institute for Information Freedom Development"
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
from copy import copy

from exmo2010.models import Score, Task, Organization
from exmo2010.urls import crumbs_tree

from .middleware import BreadcrumbsMiddleware, crumbs_dict


class ExmoBreadcrumbsMiddleware(BreadcrumbsMiddleware):
    def __init__(self):
        self.expert_crumbs = crumbs_dict(crumbs_tree(is_expert=True))
        self.nonexpert_crumbs = crumbs_dict(crumbs_tree(is_expert=False))

    def get_crumbs_dict(self, request):
        ''''''
        if hasattr(request.user, 'profile') and request.user.profile.is_expert:
            return self.expert_crumbs
        else:
            return self.nonexpert_crumbs

    def infer_kwargs(self, initial_kwargs):
        '''
        Infer all needed kwargs for parent crumbs patterns.

        :param initial_kwargs: kwargs for currently requested url

        :returns: dict -- all inferred kwargs
        '''
        kwargs = copy(initial_kwargs)
        if 'score_pk' in kwargs:
            score = kwargs.get('score')
            if not score:
                score = Score.objects.select_related('task.organization.monitoring')\
                                        .get(pk=kwargs['score_pk'])
            kwargs['task'] = score.task
            kwargs['task_pk'] = score.task.pk

        if 'task_pk' in kwargs:
            task = kwargs.get('task')
            if not task:
                task = Task.objects.select_related('organization.monitoring')\
                                    .get(pk=kwargs['task_pk'])
            kwargs['org'] = task.organization
            kwargs['org_pk'] = task.organization.pk

        if 'org_pk' in kwargs:
            org = kwargs.get('org')
            if not org:
                org = Organization.objects.select_related('monitoring')\
                                            .get(pk=kwargs['org_pk'])
            kwargs['monitoring_pk'] = org.monitoring.pk

        return kwargs
