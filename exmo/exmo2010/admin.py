import exmo.exmo2010.models
from django.contrib import admin

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
admin.site.register(exmo.exmo2010.models.Score)
admin.site.register(exmo.exmo2010.models.Entity)
admin.site.register(exmo.exmo2010.models.Federal, FederalAdmin)
admin.site.register(exmo.exmo2010.models.Link)
