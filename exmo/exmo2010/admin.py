from exmo.exmo2010.models import Score, Organization, Category, Subcategory, Parameter, Criteria
from django.contrib import admin

class ScoreAdmin(admin.ModelAdmin):
  #list_filter   = ('organization', 'author')
  list_display  = ('organization', 'parameter', 'criteria')

admin.site.register(Score, ScoreAdmin)
admin.site.register(Organization)
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Parameter)
admin.site.register(Criteria)
