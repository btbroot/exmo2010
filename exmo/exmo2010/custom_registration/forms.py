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
from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from annoying.decorators import autostrip

PASSWORD_ALLOWED_CHARS = string.ascii_letters + string.digits

SEX_CHOICES = (
    (1, _("male")),
    (2, _("female")),
    )


@autostrip
class RegistrationForm(forms.Form):
    """Форма регистрации.
    На имя и отчество выделено по 15 символов, чтобы они вместе вместились
    в поле first_name модели User.
    """
    first_name = forms.CharField(label=_("First name"),
        help_text=_("Enter your first name in order the system can address "
                    "you with it."),
        widget=forms.TextInput(attrs={"maxlength": 14}),
        required=False, max_length=14)
    patronymic = forms.CharField(label=_("Patronymic"),
        help_text=_("Enter your patronymic in order the system can address "
                    "you with it."),
        widget=forms.TextInput(attrs={"maxlength": 14}),
        required=False, max_length=14)
    last_name = forms.CharField(label=_("Last name"),
        help_text=_("Enter your last name in order the system can address "
                    "you with it."),
        widget=forms.TextInput(attrs={"maxlength": 30}),
        required=False, max_length=30)
    email = forms.EmailField(label="E-mail",
        help_text=_("E-mail is required for confirming registration and "
                    "loggin in."),
        widget=forms.TextInput({"maxlength": 75}))
    password = forms.CharField(label=_("Password"),
        widget=forms.TextInput(attrs={"maxlength": 24}),
        help_text=_("Create a complicated password using latin characters (A-Z, a-z) and digits (0-9)."))
    sex = forms.ChoiceField(label=_("Sex"), choices=SEX_CHOICES,
        widget=forms.RadioSelect(),
        required=False)
    invitation_code = forms.CharField(label=_("Invitation code"),
        help_text=_("If you don't have invitation code, leave this field "
                    "empty."),
        widget=forms.TextInput(attrs={"maxlength": 6}),
        required=False, max_length=6, min_length=6)
    subscribe = forms.BooleanField(label="",
        help_text=_("Subscribe to news e-mail notification"),
        required=False)

    def clean_password(self):
        """Проверка пароля на наличие недопустимых символов."""
        password = self.cleaned_data.get('password')
        for char in password:
            if char not in PASSWORD_ALLOWED_CHARS:
                raise forms.ValidationError(_("Password contains unallowed "
                                              "characters. Please use only latin letters and digits."))
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
                                          "use. Please supply a different email address."))
        return email

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.label_suffix = ""  # Убираем двоеточие после названия поля.


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
                                              "characters. Please use only latin letters and digits."))
        return password

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(SetPasswordForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['new_password'])
        if commit:
            self.user.save()
        return self.user
