import exmo.exmo2010.models
from django.contrib import admin
from reversion.admin import VersionAdmin


from django.shortcuts import get_object_or_404
class ScoreAdmin(VersionAdmin):

    radio_fields = {
	"found": admin.HORIZONTAL,
	"complete": admin.HORIZONTAL,
	"topical": admin.HORIZONTAL,
	"accessible": admin.HORIZONTAL,
    }

    readonly_fields = ('task', 'parameter',)

    def queryset(self, request):
        if request.user.is_superuser:
            qs = self.model._default_manager.get_query_set()
        else:
            qs = self.model._default_manager.get_query_set().filter(user = request.user)

        ordering = self.ordering or ()
        if ordering:
            qs = qs.order_by(*ordering)
        return qs


    # A template for a very customized change view:
    change_form_template = 'admin/score_change_form.html'

    def change_view(self, request, object_id, extra_context=None):
	parameter = get_object_or_404(exmo.exmo2010.models.Score, pk=object_id).parameter

	main_fieldset = (
	  ('main', {
	    'fields': ('task','parameter','found',),
	  })
	)
	comment_fieldset = (
	  ('comment', {
	    'classes': ('collapse',),
	    'fields': ('comment',)
	  })
	)
	ct = at = tt = None
	if parameter.completeRequired:
          ct = ('complete', {'fields': ('complete', 'completeComment',)})

	if parameter.topicalRequired:
          tt = ('topical', {
            'fields': ('topical', 'topicalComment',)
          })
	if parameter.accessibleRequired:
          at = ('accessible', {
            'fields': ('accessible', 'accessibleComment',)
          })
        if ct and tt and at:
          self.fieldsets = main_fieldset, ct, tt, at, comment_fieldset
        elif ct and tt:
          self.fieldsets = main_fieldset, ct, tt, comment_fieldset
        elif ct and at:
          self.fieldsets = main_fieldset, ct, at, comment_fieldset
        elif at and tt:
          self.fieldsets = main_fieldset, tt, at, comment_fieldset
        return super(ScoreAdmin, self).change_view(request, object_id,
            extra_context={ 'parameter': parameter })

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
