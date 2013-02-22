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

"""
 Модуль с классом пригодным для использования как authentication backend
"""

from exmo2010.auth.helpers import check_permission

class ObjectPermBackend(object):
    """
     Это бекенд для получения прав для объекта
     Сделан по описанию https://docs.djangoproject.com/en/1.3/topics/auth/#handling-object-permissions
     Имеет один активный метод -- has_perm который принимает и обрабатывает obj -- объект для которого проверяет привелегия
     По сути django-врапер для check_permission
    """
    supports_object_permissions = True
    supports_anonymous_user = True

    def authenticate(self, username, password):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        return check_permission(user_obj, perm, obj)
