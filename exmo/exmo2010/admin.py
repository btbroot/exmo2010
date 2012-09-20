# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
import exmo2010.models
from django.contrib import admin
from reversion.admin import VersionAdmin
from django.db import models
from django.contrib.auth.admin import UserAdmin

UserAdmin.filter_horizontal = ('user_permissions', 'groups')

class ParameterAdmin(VersionAdmin):
    list_display = search_fields = ('code','name',)
    list_filter = ('monitoring', 'npa')
    formfield_overrides = {
        models.ManyToManyField: {
            'widget': admin.widgets.FilteredSelectMultiple('',
                                                           is_stacked=False)
        },
    }
    class Media:
        css = {
            "all": ("exmo2010/selector.css",)
        }

class TaskAdmin(VersionAdmin):
    search_fields = ('user__username', 'organization__name')
    list_display = ('user', 'organization',)
    list_filter = ('user','status')

class ScoreAdmin(VersionAdmin):
    list_filter = ('revision',)

class OrganizationAdmin(VersionAdmin):
  list_display = ('pk', 'name', 'inv_code')
  search_fields = ('name', 'inv_code')
  list_filter = ('monitoring',)
  readonly_fields = ('inv_code',)

class MonitoringAdmin(VersionAdmin):
  list_display = ('name',)

class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ('user__username', )
    formfield_overrides = {
        models.ManyToManyField: {
            'widget': admin.widgets.FilteredSelectMultiple('',
                                                           is_stacked=False)
        },
    }
    class Media:
        css = {
            "all": ("exmo2010/selector.css",)
        }



from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from exmo2010.models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fk_name = 'user'
    max_num = 1
    formfield_overrides = {
        models.ManyToManyField: {
            'widget': admin.widgets.FilteredSelectMultiple('',
                                                           is_stacked=False)
        },
    }
    class Media:
        css = {
            "all": ("exmo2010/selector.css",)
        }


from django.contrib.auth.admin import UserAdmin
class UserAdmin(UserAdmin):
    inlines = [UserProfileInline,]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(exmo2010.models.Organization, OrganizationAdmin)
admin.site.register(exmo2010.models.Parameter, ParameterAdmin)
admin.site.register(exmo2010.models.Score, ScoreAdmin)
admin.site.register(exmo2010.models.Task, TaskAdmin)
admin.site.register(exmo2010.models.Monitoring, MonitoringAdmin)
admin.site.register(exmo2010.models.MonitoringStatus)
admin.site.register(exmo2010.models.Claim)
admin.site.register(exmo2010.models.OpennessExpression)
