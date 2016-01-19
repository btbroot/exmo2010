# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
# Copyright 2014, 2016 IRSI LTD
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
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _

from .forms import (SettingsChPassForm, SettingsInvCodeForm, SettingsPersInfForm,
                    SettingsPersInfFormFull, SubscribeAndNotifyForm, SubscribeForm)
from exmo2010.models import Organization, UserProfile, OrgUser


@login_required
def settings(request):
    """
    User settings page.
    """
    user = request.user
    profile = user.profile
    is_organization = profile.is_organization
    is_internal = profile.is_internal()
    subscribe_form = SubscribeAndNotifyForm if (is_internal or is_organization) else SubscribeForm

    # Маркеры того, что форма уже создана.
    pers_inf_form_ready = inv_code_form_ready = ch_pass_form_ready = send_notif_form_ready = False
    # Ошибки и сообщения об успехе операций.
    # Сообщение об успехе при сабмите формы с личными данными.
    pers_inf_form_mess = False
    # Сообщение об успехе при сабмите формы с кодом приглашения.
    inv_code_form_mess = False
    # Сообщение об ошибке при сабмите формы с кодом приглашения.
    inv_code_form_err = ""
    # Сообщение об успехе при сабмите формы смены пароля.
    ch_pass_form_mess = False
    # Сообщение об ошибке при сабмите формы смены пароля.
    ch_pass_form_err = ""
    # Сообщение об успехе при сабмите формы настроек уведомлений.
    send_notif_form_mess = False
    if request.method == "POST":
        # Засабмитили форму с личными данными.
        if request.POST.has_key("first_name"):
            if is_organization:
                pers_inf_form = SettingsPersInfFormFull(request.POST)
            else:
                pers_inf_form = SettingsPersInfForm(request.POST)
            if pers_inf_form.is_valid():
                pers_inf_form_cd = pers_inf_form.cleaned_data
                first_name = pers_inf_form_cd.get("first_name", "")
                patronymic = pers_inf_form_cd.get("patronymic", "")
                if first_name and patronymic:
                    user.first_name = "%s %s".strip() % (first_name,
                                                         patronymic)
                elif first_name or patronymic:
                    user.first_name = "%s%s".strip() % (first_name,
                                                        patronymic)
                else:
                    user.first_name = ""
                user.last_name = pers_inf_form_cd.get("last_name", "")
                if is_organization:
                    position = pers_inf_form_cd.get("position", "")
                    profile.position = position
                    phone = pers_inf_form_cd.get("phone", "")
                    profile.phone = phone
                pers_inf_form_mess = True
            pers_inf_form_ready = True
        # Засабмитили форму с кодом приглашения.
        elif "invitation_code" in request.POST:
            if not is_internal:
                inv_code_form = SettingsInvCodeForm(request.POST)
                if inv_code_form.is_valid():
                    inv_code_form_cd = inv_code_form.cleaned_data
                    invitation_code = inv_code_form_cd.get("invitation_code")
                    organization = Organization.objects.get(inv_code=invitation_code)
                    og = Group.objects.get(name=UserProfile.organization_group)
                    # Безопасно так делать, даже если он уже там.
                    user.groups.add(og)
                    OrgUser.objects.get_or_create(organization=organization, userprofile=profile)
                    inv_code_form_mess = "%s: %s" % (_("You are associated with the organization with"),
                                                     organization.name)
                    is_organization = True
                    subscribe_form = SubscribeAndNotifyForm
                else:
                    inv_code_form_err = _("Submitted invitation code does not exist.")
                    inv_code_form_ready = True
        # Засабмитили форму смены пароля.
        elif "old_password" in request.POST:
            ch_pass_form = SettingsChPassForm(request.POST, user=user)
            if ch_pass_form.is_valid():
                ch_pass_form_cd = ch_pass_form.cleaned_data
                new_password = ch_pass_form_cd.get("new_password")
                user.set_password(new_password)
                ch_pass_form_mess = _("Password changed")
            else:
                ch_pass_form_err = True
                ch_pass_form_ready = True
        # Засабмитили форму настроек уведомлений.
        elif "notify_submit" in request.POST:
            send_notif_form = subscribe_form(request.POST, instance=user.profile)
            if send_notif_form.is_valid():
                send_notif_form.save()
                send_notif_form_mess = _("E-mail notification settings saved")
            send_notif_form_ready = True
        profile.save()
        user.save()

    # Создание форм при GET-запросе, а также прочих, кроме засабмиченой
    # при POST-запросе.
    if not pers_inf_form_ready:
        pers_inf_form_indata = {}  # Для 1-й формы.
        first_name_parts = user.first_name.split()
        # Имя и отчество храним разделенными пробелом
        # в поле first_name модели User.
        if first_name_parts:
            pers_inf_form_indata["first_name"] = first_name_parts[0]
            if len(first_name_parts) > 1:
                pers_inf_form_indata["patronymic"] = first_name_parts[1]
        if user.last_name:
            pers_inf_form_indata["last_name"] = user.last_name
        if is_organization:
            if profile.position:
                pers_inf_form_indata["position"] = profile.position
            if profile.phone:
                pers_inf_form_indata["phone"] = profile.phone
            pers_inf_form = SettingsPersInfFormFull(
                initial=pers_inf_form_indata)
        else:
            pers_inf_form = SettingsPersInfForm(initial=pers_inf_form_indata)

    if not inv_code_form_ready:
        inv_code_form = SettingsInvCodeForm()

    if not ch_pass_form_ready:
        ch_pass_form = SettingsChPassForm(user=user)

    if not send_notif_form_ready:
        send_notif_form = subscribe_form(instance=user.profile)

    return TemplateResponse(request, 'user_settings.html', {
        "email": user.email,
        "is_organization": is_organization,
        "is_internal": is_internal,
        "pers_inf_form": pers_inf_form,
        "inv_code_form": inv_code_form,
        "ch_pass_form": ch_pass_form,
        "send_notif_form": send_notif_form,
        "pers_inf_form_mess": pers_inf_form_mess,
        "inv_code_form_mess": inv_code_form_mess,
        "ch_pass_form_mess": ch_pass_form_mess,
        "send_notif_form_mess": send_notif_form_mess,
        "inv_code_form_err": inv_code_form_err,
        "ch_pass_form_err": ch_pass_form_err
    })
