# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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
from django.db import models
from reversion.admin import VersionAdmin

from exmo2010.models import Parameter


class ParameterAdmin(VersionAdmin):
    list_display = search_fields = ('code', 'name',)
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

admin.site.register(Parameter, ParameterAdmin)
