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
from exmo2010.forms import OrgUserSettingsForm, OrdinaryUserSettingsForm
from exmo2010.forms import OurUserSettingsForm
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User, Group
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseForbidden, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from exmo2010.models import Organization, UserProfile


def settings(request):
    """Страница настроек пользователя."""
    success = False
    if not request.user.is_authenticated():
        raise Http404
    user = request.user
    profile = user.get_profile()
    if profile.is_internal():  # Наш сотрудник.
        form_class = OurUserSettingsForm
    elif profile.is_organization:
        form_class = OrgUserSettingsForm
    else:
        form_class = OrdinaryUserSettingsForm
    if request.method == "POST":
        form = form_class(request.POST, user=user)
        if form.is_valid():
            cd = form.cleaned_data
            # Поля, присутствующие у всех.
            first_name = cd.get("first_name", "")
            patronymic = cd.get("patronymic", "")
            user.first_name = "%s %s".strip() % (first_name, patronymic)
            user.last_name = cd.get("last_name", "")
            subscribe = cd.get("subscribe", False)
            profile.subscribe = subscribe
            new_password = cd.get("new_password")
            if new_password:
                user.set_password(new_password)
            # Поля, присутствующие у наших внутренних пользователей
            # и представителей организаций.
            if profile.is_internal() or profile.is_organization:
                cnt = cd.get("comment_notification_type")
                if not cnt:
                    cnt = 0
                else:
                    cnt = int(cnt)
                nmc = cd.get("notify_on_my_comments")
                try:
                    nmc = int(nmc)
                except (ValueError, TypeError):
                    nmc = 0
                nmc = bool(nmc)
                comment_pref = {"type": cnt, "self": nmc}
                if cnt == 2:
                    cnd = cd.get("comment_notification_digest", 1)
                    if not cnd:
                        cnd = 1
                    else:
                        cnd = int(cnd)
                    comment_pref["digest_duratation"] = cnd
                profile.notify_comment_preference = comment_pref

                snt = cd.get("score_notification_type")
                if not snt:
                    snt = 0
                else:
                    snt = int(snt)
                score_pref = {"type": snt}
                if snt == 2:
                    snd = cd.get("score_notification_digest", 1)
                    if not snd:
                        snd = 1
                    else:
                        snd = int(snd)
                    score_pref["digest_duratation"] = snd
                profile.notify_score_preference = score_pref

                if profile.is_organization:
                    # Поля, присутствующие только у представителей организаций.
                    position = cd.get("position", "")
                    profile.position = position
                    phone = cd.get("phone", "")
                    profile.phone = phone
            # Поля, присутствующие только у обычных пользователей (внешние, но
            # не представители организаций).
            else:
                invitation_code = cd.get("invitation_code", "")
                if invitation_code:
                    try:
                        organization = Organization.objects.get(
                            inv_code=invitation_code)
                    except ObjectDoesNotExist:
                        pass
                    else:
                        og_name = UserProfile.organization_group
                        og = Group.objects.get(name=og_name)
                        user.groups.add(og)
                        profile.organization.add(organization)
            profile.save()
            user.save()
            success = True
    else:
        initial_data = {}
        if user.email:
            initial_data["email"] = user.email
        first_name_parts = user.first_name.split()
        # Имя и отчество храним разделенными пробелом
        # в поле first_name модели User.
        if first_name_parts:
            initial_data["first_name"] = first_name_parts[0]
            if len(first_name_parts) > 1:
                initial_data["patronymic"] = first_name_parts[1]
        if user.last_name:
            initial_data["last_name"] = user.last_name
        if profile.subscribe:
            initial_data["subscribe"] = profile.subscribe
        if profile.is_internal() or profile.is_organization:
            score_pref = profile.notify_score_preference
            comment_pref = profile.notify_comment_preference
            initial_data["comment_notification_type"] = comment_pref['type']
            initial_data["comment_notification_digest"] = \
                comment_pref['digest_duratation']
            initial_data["notify_on_my_comments"] = int(comment_pref['self'])
            initial_data["score_notification_type"] = score_pref['type']
            initial_data["score_notification_digest"] = \
                score_pref['digest_duratation']
            if profile.is_organization:
                if profile.position:
                    initial_data["position"] = profile.position
                if profile.phone:
                    initial_data["phone"] = profile.phone
        form = form_class(initial=initial_data, user=user)
    return render_to_response('exmo2010/user_settings.html',
        {"form": form, "success": success},
        context_instance=RequestContext(request))


from admin_tools.dashboard.models import DashboardPreferences
@csrf_protect
def user_reset_dashboard(request):
    if request.method == 'POST':
        if request.user.is_active:
            try:
                pref = DashboardPreferences.objects.get(dashboard_id = 'exmo2010', user = request.user)
                pref.data = '{}'
                pref.save()
            except DashboardPreferences.DoesNotExist:
                pass
        messages.add_message(request, messages.INFO, _('Dashboard preferences was reset.'))
        return HttpResponseRedirect(reverse('exmo2010:user_profile'))
    else:
        return HttpResponseForbidden(_('Forbidden'))
