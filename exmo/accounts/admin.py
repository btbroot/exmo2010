# -*- coding: utf-8 -*-
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
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import ManyToManyField

from exmo2010.models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fk_name = 'user'
    max_num = 1
    formfield_overrides = {
        ManyToManyField: {
            'widget': FilteredSelectMultiple('', is_stacked=False)
        },
    }

    class Media:
        css = {
            "all": ("exmo2010/css/selector.css",)
        }


class CustomUserAdmin(UserAdmin):
    filter_horizontal = ('user_permissions', 'groups')
    inlines = [UserProfileInline, ]


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


class CustomGroupAdmin(GroupAdmin):
    class Media:
        css = {
            "all": ("exmo2010/css/selector.css",)
        }


admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)
