# Copyright 2010 Al Nikolov <root@toor.spb.ru>, Helsinki, Finland
# Copyright 2010 Institute of Information Freedom Development, non-profit partnership, Saint-Petersburg, Russia
#
# This file is part of EXMO2010 software.
#
# EXMO2010 is NOT distributable. NOBODY is permitted to use it without a written permission from the
# above copyright holders.
import exmo.exmo2010.models
from django.contrib import admin
from reversion.admin import VersionAdmin

class ScoreAdmin(VersionAdmin):
    pass

class OrganizationTypeAdmin(admin.ModelAdmin):
  list_display = ('pk', 'name')

class OrganizationAdmin(admin.ModelAdmin):
  list_display = ('pk', 'name')

class FederalAdmin(admin.ModelAdmin):
  list_display = ('pk', 'name')

admin.site.register(exmo.exmo2010.models.Organization, OrganizationAdmin)
admin.site.register(exmo.exmo2010.models.Category)
admin.site.register(exmo.exmo2010.models.Subcategory)
admin.site.register(exmo.exmo2010.models.Parameter)
admin.site.register(exmo.exmo2010.models.OrganizationType, OrganizationTypeAdmin)
admin.site.register(exmo.exmo2010.models.Score, ScoreAdmin)
admin.site.register(exmo.exmo2010.models.Entity)
admin.site.register(exmo.exmo2010.models.Federal, FederalAdmin)
admin.site.register(exmo.exmo2010.models.Task)
