# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
import hashlib
import random

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import Group, User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import translation
from registration import signals
from registration.backends import get_backend as get_registration_backend
from registration.backends.default import DefaultBackend
from registration.models import RegistrationProfile

from exmo2010.custom_registration.forms import RegistrationFormFull, RegistrationFormShort
from exmo2010.mail import mail_register_activation
from exmo2010.models import UserProfile, Organization


def get_backend(path):
    if not path:
        path = getattr(settings, 'CUSTOM_REGISTRATION_BACKEND')

    return get_registration_backend(path)


class CustomBackend(DefaultBackend):
    """
    A registration backend which follows a simple workflow:

    1. User signs up, inactive account is created.

    2. Email is sent to user with activation link.

    3. User clicks activation link, account is now active.

    Using this backend requires that

    * ``registration`` be listed in the ``INSTALLED_APPS`` setting
      (since this backend makes use of models defined in this
      application).

    * The setting ``ACCOUNT_ACTIVATION_DAYS`` be supplied, specifying
      (as an integer) the number of days from registration during
      which a user may activate their account (after that period
      expires, activation will be disallowed).

    * The creation of the templates
      ``registration/activation_email_subject.txt`` and
      ``registration/activation_email.html``, which will be used for
      the activation email. See the notes for this backends
      ``register`` method for details regarding these templates.

    Additionally, registration can be temporarily closed by adding the
    setting ``REGISTRATION_OPEN`` and setting it to
    ``False``. Omitting this setting, or setting it to ``True``, will
    be interpreted as meaning that registration is currently open and
    permitted.

    Internally, this is accomplished via storing an activation key in
    an instance of ``registration.models.RegistrationProfile``. See
    that model and its custom manager for full documentation of its
    fields and supported operations.

    """
    def register(self, request, **kwargs):
        """
        Given a username, email address and password, register a new
        user account, which will initially be inactive.

        Along with the new ``User`` object, a new
        ``registration.models.RegistrationProfile`` will be created,
        tied to that ``User``, containing the activation key which
        will be used for this account.

        An email will be sent to the supplied email address; this
        email should contain an activation link. The email will be
        rendered using two templates. See the documentation for
        ``RegistrationProfile.send_activation_email()`` for
        information about these templates and the contexts provided to
        them.

        After the ``User`` and ``RegistrationProfile`` are created and
        the activation email is sent, the signal
        ``registration.signals.user_registered`` will be sent, with
        the new ``User`` as the keyword argument ``user`` and the
        class of this backend as the sender.

        """
        with transaction.commit_on_success():
            new_user = User.objects.create_user(kwargs['email'], kwargs['email'], kwargs['password'])
            new_user.is_active = False
            new_user.save()

            salt = hashlib.sha1(str(random.random())).hexdigest()[:5]
            name = new_user.username
            if isinstance(name, unicode):
                name = name.encode('utf-8')
            activation_key = hashlib.sha1(salt + name).hexdigest()

            RegistrationProfile.objects.create(user=new_user, activation_key=activation_key)

        mail_register_activation(request, new_user, activation_key)

        # Сохраняем дополнительные поля модели User.
        user_changed = False
        first_name = kwargs.get("first_name", "").capitalize()
        patronymic = kwargs.get("patronymic", "").capitalize()
        if first_name and patronymic:
            first_name = "%s %s" % (first_name, patronymic)
            new_user.first_name = first_name
            user_changed = True
        elif first_name or patronymic:
            first_name = "%s%s" % (first_name, patronymic)
            new_user.first_name = first_name
            user_changed = True
        last_name = kwargs.get("last_name", "").capitalize()
        if last_name:
            new_user.last_name = last_name
            user_changed = True
        if user_changed:
            new_user.save()
        # Сохраняем поля профиля пользователя.
        user_profile = UserProfile.objects.get_or_create(user=new_user)[0]
        subscribe = kwargs.get("subscribe")
        if subscribe:
            user_profile.subscribe = subscribe
        status = int(kwargs.get("status"))
        if status == 0:  # представитель организации.
            position = kwargs.get("position")
            if position:
                user_profile.position = position
            phone = kwargs.get("phone")
            if phone:
                user_profile.phone = phone
            invitation_code = kwargs.get("invitation_code")
            if invitation_code:
                try:
                    organization = Organization.objects.get(
                        inv_code=invitation_code)
                except ObjectDoesNotExist:
                    pass
                else:
                    og_name = UserProfile.organization_group
                    og = Group.objects.get(name=og_name)
                    new_user.groups.add(og)
                    user_profile.organization.add(organization)
        # set language preference
        language = translation.get_language_from_request(request, check_path=True)
        user_profile.language = language

        user_profile.save()

        signals.user_registered.send(sender=self.__class__, user=new_user, request=request)
        return new_user

    def activate(self, request, activation_key):
        """
        Given an an activation key, look up and activate the user
        account corresponding to that key (if possible).

        After successful activation, the signal
        ``registration.signals.user_activated`` will be sent, with the
        newly activated ``User`` as the keyword argument ``user`` and
        the class of this backend as the sender.

        """
        activated = RegistrationProfile.objects.activate_user(activation_key)
        if activated:
            activated.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, activated)
            signals.user_activated.send(sender=self.__class__,
                                        user=activated,
                                        request=request)
        return activated

    def get_form_class(self, request):
        """
        Return the default form class used for user registration.

        """
        form_class = RegistrationFormFull
        if request.method == 'POST':
            if not 'invitation_code' in request.POST:
                form_class = RegistrationFormShort

        return form_class
