# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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

from annoying.decorators import autostrip
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import UNUSABLE_PASSWORD
from django.contrib.auth.models import User
from django.db.models import Q
from django.db import transaction
from django.utils.translation import get_language_from_request, ugettext_lazy as _
from django.utils.decorators import method_decorator

from exmo2010.models import UserProfile


PASSWORD_ALLOWED_CHARS = string.ascii_letters + string.digits

STATUS_CHOICES = (
    ('representative', _('representative')),
    ('individual', _('private person')),
)


@autostrip
class RegistrationForm(forms.Form):
    """
    Укороченная форма регистрации.
    Используется, если выбран статус "интересующийся гражданин".
    На имя и отчество выделено по 15 символов, чтобы они вместе вместились
    в поле first_name модели User.
    """
    first_name = forms.CharField(
        label=_("First name"), required=False, widget=forms.TextInput(attrs={"maxlength": 14}))
    patronymic = forms.CharField(
        label=_("Patronymic"), required=False,  widget=forms.TextInput(attrs={"maxlength": 14}))
    last_name = forms.CharField(
        label=_("Last name"), required=False, widget=forms.TextInput(attrs={"maxlength": 30}))
    email = forms.EmailField(label=_("E-mail"), widget=forms.TextInput({"maxlength": 75}))
    password = forms.CharField(
        label=_("Password"), widget=forms.TextInput(attrs={"maxlength": 24, "autocomplete": "off"}))
    subscribe = forms.BooleanField(label=_("Subscribe to news"), required=False)
    position = forms.CharField(label=_("Job title"), required=False, widget=forms.TextInput(attrs={"maxlength": 48}))
    phone = forms.CharField(label=_("Phone number"), required=False, widget=forms.TextInput(attrs={"maxlength": 30}))
    invitation_code = forms.CharField(label=_("Invitation code"), required=False, widget=forms.TextInput(attrs={"maxlength": 6}))

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        fields = 'first_name patronymic last_name position phone email password invitation_code subscribe'
        self.fields.keyOrder = fields.split()

    def clean_password(self):
        """Проверка пароля на наличие недопустимых символов."""
        password = self.cleaned_data.get('password')
        for char in password:
            if char not in PASSWORD_ALLOWED_CHARS:
                raise forms.ValidationError(_(
                    "Password contains unallowed characters. Please use only latin letters and digits."))
        return password

    def clean_email(self):
        """
        Validate that the supplied email address is unique for the site.

        """
        email = self.cleaned_data['email']
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            raise forms.ValidationError(_(
                "This email address is already in use. Please supply a different email address."))
        return email

    def clean_invitation_code(self):
        """
        Return list of invitation codes or empty list.
        TODO: check whether invitation code exists.
        """
        return filter(None, self.cleaned_data.get('invitation_code', '').split(','))

    @method_decorator(transaction.commit_on_success)
    def save(self, request):
        data = self.cleaned_data
        user = User.objects.create_user(data['email'], data['email'], data['password'])

        user.is_active = False

        first_name = data.get("first_name", "").capitalize()
        patronymic = data.get("patronymic", "").capitalize()
        if first_name and patronymic:
            user.first_name = "%s %s" % (first_name, patronymic)
        else:
            user.first_name = first_name or patronymic or ''
        user.last_name = data.get("last_name", "").capitalize()
        user.save()

        profile = UserProfile.objects.get_or_create(user=user)[0]
        profile.subscribe = data.get("subscribe", False)
        profile.position = data.get("position", None)
        profile.phone = data.get("phone", None)
        # Set language preference
        profile.language = get_language_from_request(request, check_path=True)
        profile.email_confirmed = False
        profile.save()

        return user


@autostrip
class SetPasswordForm(forms.Form):
    new_password = forms.CharField(label=_("New password"), widget=forms.TextInput)

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        for char in password:
            if char not in PASSWORD_ALLOWED_CHARS:
                raise forms.ValidationError(_(
                    "Password contains unallowed characters. Please use only latin letters and digits."))
        return password


class LoginForm(forms.Form):
    username = forms.CharField(label=_("E-mail"), max_length=30)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user = authenticate(username=username, password=password)
            if self.user is None:
                raise forms.ValidationError(_(
                    "Please enter a correct username and password. Note that both fields are case-sensitive."))
            elif not self.user.profile.email_confirmed:
                raise forms.ValidationError(_(
                    "This account is inactive. Did you receive the letter containing a registration confirmation link?"))
            elif not self.user.is_active:
                # User is banned.
                raise forms.ValidationError(_("This account is inactive."))
        return self.cleaned_data


class ExistingEmailForm(forms.Form):
    email = forms.EmailField(label=_("E-mail"), max_length=75)

    def clean_email(self):
        """
        Проверяет присутствие пользователя в базе с этой почтой
        """
        email = self.cleaned_data['email']
        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except ObjectDoesNotExist:
                raise forms.ValidationError(_(
                    "That e-mail address doesn't have an associated user account. Are you sure you've registered?"))
            banned = user.profile.email_confirmed and not user.is_active
            if banned or user.password == UNUSABLE_PASSWORD:
                raise forms.ValidationError(_("The user account associated with this e-mail was suspended."))
        return email
