# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2015 IRSI LTD
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
from django.contrib.admin.util import unquote
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.utils import DEFAULT_DB_ALIAS
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text
from django.views.decorators.csrf import csrf_protect
from modeltranslation.admin import TranslationAdmin, TabbedTranslationAdmin
from reversion.admin import VersionAdmin

from . import models
from core.admin_utils import VerboseAdminMixin


def register(model):
    def wrapper(cls):
        admin.site.register(model, cls)
        return cls
    return wrapper


admin.site.register(models.OpennessExpression)


@register(models.Monitoring)
class MonitoringAdmin(TranslationAdmin):
    list_display = ('name',)

    @method_decorator(csrf_protect)
    @transaction.commit_on_success
    def delete_view(self, request, object_id, extra_context=None):
        """
        This method was copied from contrib.admin with changes to prevent memory exhaustion.
        Unfortunately overriding this whole method is the only way we can customize deletion as needed.
        NOTE: If in the future django releases we will be able to customize usage of
        contrib.admin.util.get_deleted_objects by default implementation of this view, this may be simplified.
        """
        opts = self.model._meta
        app_label = opts.app_label

        obj = self.get_object(request, unquote(object_id))

        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            errdata = {'name': force_text(opts.verbose_name), 'key': escape(object_id)}
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % errdata)

        if request.POST:  # The user has already confirmed the deletion.
            obj_display = force_text(obj)
            self.log_deletion(request, obj, obj_display)

            # To prevent memory exhaustion use _raw_delete() for scores and models below (BUG 2249)
            # TODO: after rewrite of comments code, delete score comments here, before scores deletion.
            models.Claim.objects.filter(score__parameter__monitoring=obj)._raw_delete(using=DEFAULT_DB_ALIAS)
            models.Clarification.objects.filter(score__parameter__monitoring=obj)._raw_delete(using=DEFAULT_DB_ALIAS)
            models.Score.objects.filter(parameter__monitoring=obj)._raw_delete(using=DEFAULT_DB_ALIAS)

            # Delete monitoring normally. This will still try to fetch scores, but they got deleted above and
            # should not consume all memory.
            obj.delete()

            msgdata = {'name': force_text(opts.verbose_name), 'obj': force_text(obj_display)}
            self.message_user(request, _('The %(name)s "%(obj)s" was deleted successfully.') % msgdata)

            if not self.has_change_permission(request, None):
                return HttpResponseRedirect(reverse('admin:index', current_app=self.admin_site.name))

            urlname = 'admin:%s_%s_changelist' % (opts.app_label, opts.module_name)
            return HttpResponseRedirect(reverse(urlname, current_app=self.admin_site.name))

        object_name = force_text(opts.verbose_name)

        if not request.user.has_perm('exmo2010.delete_monitoring', obj):
            title = _("Cannot delete %(name)s") % {"name": object_name}
        else:
            title = _("Are you sure?")

        context = {
            "title": title,
            "object_name": object_name,
            "object": obj,
            "deleted_objects": [],  # TODO: show at least some deleted objects.
            "perms_lacking": [],
            "protected": [],
            "opts": opts,
            "app_label": app_label,
        }
        context.update(extra_context or {})

        return TemplateResponse(request, self.delete_confirmation_template or [
            "admin/%s/%s/delete_confirmation.html" % (app_label, opts.object_name.lower()),
            "admin/%s/delete_confirmation.html" % app_label,
            "admin/delete_confirmation.html"
        ], context, current_app=self.admin_site.name)


@register(models.Organization)
class OrganizationAdmin(TranslationAdmin, VersionAdmin):
    list_display = ('pk', 'name', 'inv_code')
    search_fields = ('name', 'inv_code', 'id')
    list_filter = ('monitoring',)
    readonly_fields = ('inv_code',)


@register(models.Parameter)
class ParameterAdmin(TabbedTranslationAdmin, VersionAdmin):
    class Media:
        css = {"all": ("exmo2010/css/selector.css",)}

    raw_id_fields = ('exclude',)
    list_display = search_fields = ('code', 'name',)
    list_filter = ('monitoring', 'npa')


@register(models.StaticPage)
class StaticPageAdmin(TabbedTranslationAdmin):
    list_display = search_fields = ('id', 'description')


@register(models.LicenseTextFragments)
class LicenseTextFragmentsAdmin(TabbedTranslationAdmin):
    list_display = ('id', 'page_footer', 'csv_footer', 'json_name', 'json_url', 'json_rightsholder', 'json_source')


@register(models.FeedbackItem)
class FeedbackItemAdmin(admin.ModelAdmin):
    list_display = ('created', 'header')


@register(models.FrontPageTextFragments)
class FrontPageTextFragmentsAdmin(TabbedTranslationAdmin):
    list_display = ('id',)
    readonly_fields = ('id',)


@register(models.ObserversGroup)
class ObserversGroupAdmin(admin.ModelAdmin):
    list_display = search_fields = ('name',)
    raw_id_fields = ('organizations', 'users')
    list_filter = ('monitoring',)


class OrgUserInline(VerboseAdminMixin, admin.StackedInline):
    model = models.OrgUser
    fk_name = 'userprofile'
    raw_id_fields_verbose = ('organization', )
    extra = 0


@register(models.UserProfile)
class UserProfileAdmin(VerboseAdminMixin, admin.ModelAdmin):
    search_fields = ('user__username', 'user__email',)
    readonly_fields = ('user', )
    inlines = [OrgUserInline, ]


@register(models.OrgUser)
class OrgUserAdmin(VerboseAdminMixin, admin.ModelAdmin):
    list_display = ('userprofile', 'organization')
    search_fields = ('userprofile__user__username', 'organization__name', 'organization__monitoring__name')
    raw_id_fields = ('userprofile', 'organization',)
    list_filter = ('organization__monitoring',)


class UserProfileInline(VerboseAdminMixin, admin.StackedInline):
    model = models.UserProfile
    fk_name = 'user'
    max_num = 1

    # NOTE: Sadly enough orgusers can't be edited here since custom M2M model is used, see
    # https://code.djangoproject.com/ticket/9475
    # raw_id_fields_verbose = ('organization', )

    class Media:
        css = {
            "all": ("exmo2010/css/selector.css", "exmo2010/css/admin_user_edit.css")
        }


class CustomUserAdmin(UserAdmin):
    filter_horizontal = ('user_permissions', 'groups')
    inlines = [UserProfileInline, ]

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


class CustomGroupAdmin(GroupAdmin):
    class Media:
        css = {"all": ("exmo2010/css/selector.css",)}


admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)
