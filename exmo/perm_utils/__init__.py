# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013 Foundation "Institute for Information Freedom Development"
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

import re

from django.db.models import Model
from django.db.models.query import QuerySet


class ObjectPermissons(object):
    '''
    Object permissions for given user.
    By coercing to string will return list of all permissions as string
    To check for given permission use as dictionary

    >>> perms = ObjectPermissons(user, obj)
    >>> str(perms)
    "can_edit_task can_approve_task can_delete_task"
    >>> perms['can_edit_task']
    True

    '''
    def __init__(self, user, obj, perm_prefix=None):
        self.user = user
        self.obj = obj
        self.perm_prefix = perm_prefix or ''

    def __getitem__(self, perm):
        return self.user.has_perm(self.perm_prefix + perm, self.obj)

    def __iter__(self):
        perms = self.user.get_all_permissions(self.obj)
        perms = set(re.sub('^' + self.perm_prefix, '', p) for p in perms)   # strip prefix
        if hasattr(self.obj, 'current_transitions') and hasattr(self.obj, 'transitions'):
            nonstate_perms = perms - set(self.obj.transitions)
            cur_state_perms = perms & set(zip(*self.obj.current_transitions())[0])
            perms = cur_state_perms | nonstate_perms
        for perm in perms:
            yield perm

    def __unicode__(self):
        return ' '.join(self)

    __repr__ = __unicode__


class PermsQuerySet(QuerySet):
    def __init__(self, *args, **kwargs):
        self.perm_user = kwargs.pop('perm_user', None)
        self.perm_prefix = kwargs.pop('perm_prefix', '')
        super(PermsQuerySet, self).__init__(*args, **kwargs)
        self.annotate_perms()

    def annotate_perms(self, user=None, perm_prefix=None):
        if user:
            self.perm_user = user
        if perm_prefix is not None:
            self.perm_prefix = perm_prefix
        if self.perm_user and self._result_cache:
            for obj in self._result_cache:
                obj.perms = ObjectPermissons(self.perm_user, obj, self.perm_prefix)

    def _fill_cache(self, num=None):
        super(PermsQuerySet, self)._fill_cache(num)
        self.annotate_perms()

    def __len__(self):
        res = super(PermsQuerySet, self).__len__()
        self.annotate_perms()
        return res


def annotate_perms(objs, user, perm_prefix=None):
    '''
    Add 'perms' attribute to the object or all objects in the list\queryset
    object.perms will be an instance of ObjectPermissons, that holds user permissions on that object
    '''
    if isinstance(objs, QuerySet):
        clone = objs._clone(PermsQuerySet)
        clone._result_cache = objs._result_cache
        clone._iter = objs._iter
        clone.annotate_perms(user, perm_prefix)
        return clone
    elif isinstance(objs, Model):
        objs.perms = ObjectPermissons(user, objs, perm_prefix)
    elif hasattr(objs, '__iter__'):
        for obj in objs:
            obj.perms = ObjectPermissons(user, obj, perm_prefix)
    return objs


class AnnotatePermsMixin():
    perm_prefix = ''

    def render_to_response(self, context, **kwargs):
        """
        Annotate all model instances and querysets in the context and return response.
        """
        for key, value in context.iter_items():
            if isinstance(value, (QuerySet, Model)):
                context[key] = annotate_perms(value, self.request.user, self.perm_prefix)
        return super(AnnotatePermsMixin, self).render_to_response(context, **kwargs)


class ExmoPermsMixin(AnnotatePermsMixin):
    perm_prefix = 'exmo2010.'


def annotate_exmo_perms(objs, user):
    return annotate_perms(objs, user, perm_prefix='exmo2010.')
