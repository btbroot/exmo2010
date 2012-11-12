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
import string
import time
from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist
from annoying.decorators import autostrip
from exmo2010.models import Organization

PASSWORD_ALLOWED_CHARS = string.ascii_letters + string.digits

STATUS_CHOICES = (
    (0, _('representative')),
    (1, _('concerned person')),
    )


@autostrip
class RegistrationFormShort(forms.Form):
    """Укороченная форма регистрации.
    Используется, если выбран статус "интересующийся гражданин".
    На имя и отчество выделено по 15 символов, чтобы они вместе вместились
    в поле first_name модели User.
    """
    status = forms.ChoiceField(label=_("Status"), choices=STATUS_CHOICES)
    first_name = forms.CharField(label=_("First name"),
        help_text=_("Enter your first name in order the system can address "
                    "you with it"),
        widget=forms.TextInput(attrs={"maxlength": 14}),
        required=False, max_length=14)
    patronymic = forms.CharField(label=_("Patronymic"),
        help_text=_("Enter your patronymic in order the system can address "
                    "you with it"),
        widget=forms.TextInput(attrs={"maxlength": 14}),
        required=False, max_length=14)
    last_name = forms.CharField(label=_("Last name"),
        help_text=_("Enter your last name in order the system can address "
                    "you with it"),
        widget=forms.TextInput(attrs={"maxlength": 30}),
        required=False, max_length=30)
    email = forms.EmailField(label=_("E-mail"),
        help_text=_("E-mail is required for confirming registration and "
                    "loggin in"),
        widget=forms.TextInput({"maxlength": 75}))
    password = forms.CharField(label=_("Password"),
        widget=forms.TextInput(attrs={"maxlength": 24, "autocomplete": "off"}),
        help_text=_("Create a complicated password using latin characters "
                    "(A-Z, a-z) and digits (0-9)."))
    subscribe = forms.BooleanField(label="",
        help_text=_("Subscribe to news e-mail notification"),
        required=False)

    def clean_password(self):
        """Проверка пароля на наличие недопустимых символов."""
        password = self.cleaned_data.get('password')
        for char in password:
            if char not in PASSWORD_ALLOWED_CHARS:
                raise forms.ValidationError(_("Password contains unallowed "
                                              "characters. Please use only "
                                              "latin letters and digits."))
        return password

    def clean_email(self):
        """
        Validate that the supplied email address is unique for the
        site.

        """
        email = self.cleaned_data['email']
        if (User.objects.filter(email__iexact=email).exists() or
            User.objects.filter(username__iexact=email).exists()):
            raise forms.ValidationError(_("This email address is already in "
                                          "use. Please supply a different "
                                          "email address."))
        return email

    def __init__(self, *args, **kwargs):
        super(RegistrationFormShort, self).__init__(*args, **kwargs)
        self.label_suffix = ""  # Убираем двоеточие после названия поля.


@autostrip
class RegistrationFormFull(RegistrationFormShort):
    """Полная форма регистрации.
    Используется, если выбран статус "представитель организации".
    На имя и отчество выделено по 15 символов, чтобы они вместе вместились
    в поле first_name модели User.
    """
    position = forms.CharField(label=_("Seat"),
        widget=forms.TextInput(attrs={"maxlength": 48}),
        required=False, max_length=48)
    phone = forms.CharField(label=_("Phone"),
        widget=forms.TextInput(attrs={"maxlength": 30}),
        required=False, max_length=30)
    invitation_code = forms.CharField(label=_("Invitation code"),
        help_text=_("Required to get access to your organization scores"),
        widget=forms.TextInput(attrs={"maxlength": 6}),
        max_length=6, min_length=6)

    def clean_invitation_code(self):
        """
        Проверить, что код приглашения существует.
        """
        invitation_code = self.cleaned_data.get('invitation_code')
        try:
            organization = Organization.objects.get(inv_code=invitation_code)
        except ObjectDoesNotExist:
            time.sleep(3)  # Чтобы усложнить перебор.
            raise forms.ValidationError(_("Submitted invitation code does not "
                                          "exist. Please enter correct one"))
        else:
            return invitation_code
        
    def __init__(self, *args, **kwargs):
        super(RegistrationFormShort, self).__init__(*args, **kwargs)
        # Правильно упорядочиваем поля.
        self.fields.keyOrder = ['status', 'first_name', 'patronymic',
                                'last_name', 'position', 'phone', 'email',
                                'password', 'invitation_code', 'subscribe']


@autostrip
class SetPasswordForm(forms.Form):
    """
    A form that lets a user change set his/her password without
    entering the old password
    """
    new_password = forms.CharField(label=_("New password"),
        widget=forms.TextInput)

    def clean_new_password(self):
        """Проверка пароля на наличие недопустимых символов."""
        password = self.cleaned_data.get('new_password')
        for char in password:
            if char not in PASSWORD_ALLOWED_CHARS:
                raise forms.ValidationError(_("Password contains unallowed "
                                              "characters. Please use only "
                                              "latin letters and digits."))
        return password

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(SetPasswordForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['new_password'])
        if commit:
            self.user.save()
        return self.user
