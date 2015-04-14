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
from urllib import urlencode
from urlparse import parse_qs

from annoying.decorators import autostrip
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import UNUSABLE_PASSWORD
from django.contrib.auth.models import User
from django.db.models import Q
from django.db import transaction
from django.utils.safestring import mark_safe
from django.utils.translation import get_language_from_request, ugettext_lazy as _
from django.utils.decorators import method_decorator

from exmo2010.models import UserProfile


PASSWORD_ALLOWED_CHARS = string.ascii_letters + string.digits


@autostrip
class RegistrationForm(forms.Form):
    email = forms.EmailField(label=_('E-mail'), max_length=75)
    password = forms.CharField(label=_('Password'), max_length=24,
                               widget=forms.TextInput(attrs={"autocomplete": "off"}))
    # 'maxlength' should be used as widget attribute (NOT form field parameter 'max_length').
    # It doesn't allow users to enter more than one invitation code and doesn't return error
    # message when we pass several invitation codes in a hidden field.
    invitation_code = forms.CharField(label=_("Invitation code"), required=False,
                                      widget=forms.TextInput(attrs={"maxlength": 6}))
    # 'first_name' and 'patronymic' fields have a 14 characters length each,
    # so they will fit together in the 'first_name' field in User model.
    first_name = forms.CharField(label=_('First name'), max_length=14, required=False)
    patronymic = forms.CharField(label=_('Patronymic'), max_length=14, required=False)
    last_name = forms.CharField(label=_('Last name'), max_length=30, required=False)
    position = forms.CharField(label=_('Job title'), max_length=48, required=False)
    phone = forms.CharField(label=_('Phone number'), max_length=30, required=False)
    notification = forms.BooleanField(label=_('Get answers from experts on e-mail'), required=False, initial=True)

    def clean_password(self):
        """
        Check if a password contains an unallowed characters.
        """
        password = self.cleaned_data.get('password')
        for char in password:
            if char not in PASSWORD_ALLOWED_CHARS:
                raise forms.ValidationError(_(
                    "Password contains unallowed characters. Please use only latin letters and digits."))
        return password

    def clean_invitation_code(self):
        """
        Return list of invitation codes or empty list.
        TODO: check whether invitation code exists.
        """
        return filter(None, self.cleaned_data.get('invitation_code', '').split(','))

    def clean(self):
        """
        Validate that the supplied email address is unique for the site.
        """
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            raise forms.ValidationError(mark_safe(_(
                "Account with this email already exists. "
                "<a href='%s'>Log in</a> or use another email address to register.") %
                reverse('exmo2010:auth_login')))
        return self.cleaned_data

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
        profile.notification_type = data.get("notification", False)
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
    email = forms.CharField(label=_("E-mail"), max_length=30)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        getparams = kwargs.pop('getparams', None)
        self.inv_codes = parse_qs(getparams).get('code', []) if getparams else []
        super(LoginForm, self).__init__(*args, **kwargs)

    def clean(self):
        username = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user = authenticate(username=username, password=password)
            if self.user is None:
                if not User.objects.filter(username=username).exists():
                    raise forms.ValidationError(mark_safe(_(
                        "This account does not exist. Check the e-mail address or <a href='%s'>register</a>.") %
                        reverse('exmo2010:registration_form')))
                else:
                    url = reverse('exmo2010:password_reset_request')
                    url += '?{}'.format(urlencode({'code': self.inv_codes, 'email': username}, True))
                    raise forms.ValidationError(mark_safe(_(
                        "You have entered an incorrect password. "
                        "Try again or use <a href='%s'>the password recovery</a>.") % url))
            elif not self.user.profile.email_confirmed:
                url = reverse('exmo2010:auth_send_email')
                url += '?{}'.format(urlencode({'code': self.inv_codes, 'email': username}, True))
                raise forms.ValidationError(mark_safe(_(
                    "Click on the link inside the activation email. "
                    "If you have not received it, we can <a href='%s'>send the email again</a>.") % url))
            elif not self.user.is_active:
                # User is banned.
                raise forms.ValidationError(_("This account is inactive."))
        return self.cleaned_data


class ExistingEmailForm(forms.Form):
    email = forms.EmailField(label=_("E-mail"), max_length=75)

    def clean(self):
        """
        Check if active user with given email exists, and is not banned.
        """
        email = self.cleaned_data.get('email')
        if email:
            users = User.objects.filter(email__iexact=email)
            if not users:
                raise forms.ValidationError(mark_safe(_(
                    "This account does not exist. Check the e-mail address or <a href='%s'>register</a>.") %
                    reverse('exmo2010:registration_form')))
            # Try to find active user with this email, who is not banned. We can have many old users with
            # same email in database.
            for user in users:
                banned = user.profile.email_confirmed and not user.is_active
                if not banned and user.password != UNUSABLE_PASSWORD:
                    # OK, found user who is not banned.
                    break
            else:
                # All found users are banned.
                raise forms.ValidationError(_("The user account associated with this e-mail was suspended."))

        return self.cleaned_data
