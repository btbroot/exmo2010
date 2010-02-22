from exmo.exmo2010.models import Score, Organization, Parameter, Quality
from django.contrib import admin

class ScoreAdmin(admin.ModelAdmin):
  list_filter   = ('organization', 'author')
  list_display  = ('organization', 'parameter', 'quality', 'score', 'author')

admin.site.register(Score, ScoreAdmin)
admin.site.register(Organization)
admin.site.register(Parameter)
admin.site.register(Quality)
