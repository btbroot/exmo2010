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
import string
import time
from annoying.decorators import autostrip

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from exmo2010.models import Organization


COMMENT_NOTIFICATION_CHOICES = (
    (0, _('do not send')),
    (1, _('one email per one comment')),
    (2, _('one email for all in time interval')),
)

DIGEST_INTERVALS = (
    (1, _("once in 1 hour")),
    (3, _("once in 3 hours")),
    (6, _("once in 6 hours")),
    (12, _("once in 12 hours")),
    (24, _("once in 24 hours")),
)

PASSWORD_ALLOWED_CHARS = string.ascii_letters + string.digits

SCORE_CHANGE_NOTIFICATION_CHOICES = (
    (0, _('do not send')),
    (1, _('one email per one change')),
    (2, _('one email for all in time interval')),
)


@autostrip
class SettingsPersInfForm(forms.Form):
    """
    Форма для блока "Личная информация" страницы настроек пользователя.
    Версия для пользователя, не являющегося представителем организации.

    """
    # required=False у email потому, что не предполагается сабмит этого поля
    # из-за кастомного виджета.
    first_name = forms.CharField(label=_("First name"),
                                 widget=forms.TextInput(attrs={"maxlength": 14}),
                                 required=False, max_length=14)
    patronymic = forms.CharField(label=_("Patronymic"),
                                 widget=forms.TextInput(attrs={"maxlength": 14}),
                                 required=False, max_length=14)
    last_name = forms.CharField(label=_("Last name"),
                                widget=forms.TextInput(attrs={"maxlength": 30}),
                                required=False, max_length=30)


@autostrip
class SettingsPersInfFormFull(SettingsPersInfForm):
    """
    Форма для блока "Личная информация" страницы настроек пользователя.
    Версия для пользователя, являющегося представителем организации.

    """
    position = forms.CharField(label=_("Seat"),
                               widget=forms.TextInput(attrs={"maxlength": 48}),
                               required=False, max_length=48)
    phone = forms.CharField(label=_("Phone"),
                            widget=forms.TextInput(attrs={"maxlength": 30}),
                            required=False, max_length=30)


@autostrip
class SettingsInvCodeForm(forms.Form):
    """
    Форма для блока "Код приглашения" страницы настроек пользователя.

    """
    invitation_code = forms.CharField(label=_("New code"),
                                      widget=forms.TextInput(attrs={"maxlength": 6}),
                                      max_length=6, min_length=6)

    def clean_invitation_code(self):
        invitation_code = self.cleaned_data.get("invitation_code")
        try:
            organization = Organization.objects.get(inv_code=invitation_code)
        except ObjectDoesNotExist:
            time.sleep(3)  # Чтобы усложнить перебор.
            raise forms.ValidationError("")  # Текст ошибки не нужен.
        else:
            return invitation_code


class SettingsChPassForm(forms.Form):
    """
    Форма для блока "Сменить пароль" страницы настроек пользователя.

    """
    old_password = forms.CharField(label=_("Old password"),
                                   widget=forms.PasswordInput(attrs={"maxlength": 24},
                                                              render_value=True), required=False)
    new_password = forms.CharField(label=_("New password"),
                                   widget=forms.TextInput(attrs={"maxlength": 24, "autocomplete": "off"}),
                                   required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(SettingsChPassForm, self).__init__(*args, **kwargs)

    def clean_old_password(self):
        if not self.user.check_password(self.cleaned_data.get("old_password")):
            raise forms.ValidationError(_("Failed to change password: "
                                          "submitted wrong current password"))

    def clean_new_password(self):
        """Проверка пароля на наличие недопустимых символов."""
        new_password = self.cleaned_data.get('new_password')
        if not new_password:
            # Ставим заведомо недопустимый символ.
            new_password = "@"
        for char in new_password:  # Проверять на наличие пароля необязательно.
            if char not in PASSWORD_ALLOWED_CHARS:
                raise forms.ValidationError(_("Failed to change password: "
                                              "it can contain only latin "
                                              "characters (A-Z, a-z) and "
                                              "digits (0-9)"))
        return new_password


class SettingsSendNotifForm(forms.Form):
    """
    Форма для блока "Рассылка уведомлений" страницы настроек пользователя.
    Версия для пользователя, не являющегося представителем организации.

    """
    # Скрытое поле, нужное для того, чтобы однозначно идентифицировать форму,
    # т.к. при снятой галке у subscribe, django вообще не кладет
    # это поле (subscribe) в POST.
    snf = forms.IntegerField(widget=forms.HiddenInput, required=False)
    subscribe = forms.BooleanField(label="",
                                   help_text=_("Subscribe to news e-mail notification"), required=False)


class SettingsSendNotifFormFull(SettingsSendNotifForm):
    """
    Форма для блока "Рассылка уведомлений" страницы настроек пользователя.
    Версия для пользователя, являющегося представителем организации.

    """
    comment_notification_type = forms.ChoiceField(
        choices=COMMENT_NOTIFICATION_CHOICES,
        label=_('Comment notification'))
    comment_notification_digest = forms.ChoiceField(choices=DIGEST_INTERVALS,
                                                    required=False)
    score_notification_type = forms.ChoiceField(
        choices=SCORE_CHANGE_NOTIFICATION_CHOICES,
        label=_('Score change notification'))
    score_notification_digest = forms.ChoiceField(choices=DIGEST_INTERVALS,
                                                  required=False)
    notify_on_my_comments = forms.BooleanField(label="",
                                               help_text=_("Send to me my comments"), required=False)
    notify_on_all_comments = forms.BooleanField(label="",
                                                help_text=_("Send whole comment thread"), required=False)

    def __init__(self, *args, **kwargs):
        super(SettingsSendNotifFormFull, self).__init__(*args, **kwargs)
