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

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout as auth_logout, REDIRECT_FIELD_NAME, authenticate
from django.core.urlresolvers import reverse
from django.forms.fields import Field
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.middleware.csrf import REASON_NO_CSRF_COOKIE, REASON_NO_REFERER
from django.shortcuts import redirect
from django.template import Context, Template
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.utils.translation import get_language_from_request
from django.views.csrf import CSRF_FAILURE_TEMPLATE
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from exmo2010.custom_registration import tokens
from exmo2010.custom_registration.forms import (
    LoginForm, RegistrationFormFull, RegistrationFormShort, ExistingEmailForm, SetPasswordForm)
from exmo2010.mail import mail_register_activation, mail_password_reset
from exmo2010.models import Task


@csrf_protect
def password_reset_request(request, **kwargs):
    # TODO: Rate limit sending email to prevent flooding from our address.

    if request.user.is_authenticated():
        return redirect('exmo2010:index')

    if request.method == "GET":
        form = ExistingEmailForm()
    elif request.method == "POST":
        form = ExistingEmailForm(request.POST)
        if form.is_valid():
            user = User.objects.get(email__iexact=form.cleaned_data["email"])
            token = tokens.PasswordResetTokenGenerator().make_token(user)
            url = reverse('exmo2010:password_reset_confirm', args=(user.pk, token))
            mail_password_reset(request, user, url)
            return HttpResponseRedirect(reverse('exmo2010:password_reset_sent'))
    context = dict(form=form, required_error=Field.default_error_messages['required'])
    return TemplateResponse(request, 'registration/password_reset_request.html', context)


@never_cache
def password_reset_confirm(request, user_pk, token):
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        user = None

    token_generator = tokens.PasswordResetTokenGenerator()
    if user is None or not token_generator.check_token(user, token):
        return TemplateResponse(request, 'registration/password_reset_confirm.html', {'link_invalid': True})

    if request.method == 'GET':
        form = SetPasswordForm()
    elif request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            # We have to call authenticate() to properly annotate user authentication backend before login
            user = authenticate(username=user.username, password=form.cleaned_data['new_password'])
            auth_login(request, user)
            return HttpResponseRedirect(reverse('exmo2010:index'))

    return TemplateResponse(request, 'registration/password_reset_confirm.html', {'form': form})


def registration_form(request):
    form_class = RegistrationFormFull
    if request.method == 'POST':
        if not 'invitation_code' in request.POST:
            form_class = RegistrationFormShort

    if request.method == 'GET':
        form = form_class(initial={'email': request.GET.get('email')})
    elif request.method == 'POST':
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
        else:
            return TemplateResponse(request, 'cookies.html')

        form = form_class(request.POST)

        if form.is_valid():
            user = form.save(request)
            for org in form.orgs:
                if user.email in org.email:
                    # User email match org email, activate him immediately.
                    user.is_active = True
                    user.save()
                    user.profile.email_confirmed = True
                    user.profile.save()
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    auth_login(request, user)
                    tasks = Task.objects.filter(organization=org, status=Task.TASK_APPROVED)
                    if tasks and user.has_perm('exmo2010.view_task', tasks[0]):
                        return redirect('exmo2010:recommendations', task_pk=tasks[0].pk)
                    else:
                        return redirect('exmo2010:index')
            else:
                # User email does not match any org email, send him activation email message.
                token = tokens.EmailConfirmTokenGenerator().make_token(user)
                url = reverse('exmo2010:confirm_email', args=(user.pk, token))
                mail_register_activation(request, user, url)

                return redirect('exmo2010:please_confirm_email')

    request.session.set_test_cookie()

    return TemplateResponse(request, 'registration/registration_form.html', {'form': form})


def resend_email(request):
    # TODO: Rate limit sending email to prevent flooding from our address.

    if request.user.is_authenticated():
        return redirect('exmo2010:index')

    form = ExistingEmailForm()
    if request.method == "POST":
        form = ExistingEmailForm(request.POST)
        if form.is_valid():
            user = User.objects.get(email=form.cleaned_data['email'])

            token = tokens.EmailConfirmTokenGenerator().make_token(user)
            url = reverse('exmo2010:confirm_email', args=(user.pk, token))
            mail_register_activation(request, user, url)
            return HttpResponseRedirect(reverse('exmo2010:please_confirm_email'))

    return TemplateResponse(request, 'registration/resend_email_form.html', {'form': form})


def confirm_email(request, user_pk, token):
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        user = None

    if user and user.profile.email_confirmed:
        return redirect('exmo2010:index')

    token_generator = tokens.EmailConfirmTokenGenerator()
    if user is None or not token_generator.check_token(user, token):
        return redirect('exmo2010:email_confirm_error')

    if user.profile.email_confirmed:
        # Already confirmed.
        return HttpResponseRedirect(settings.LOGIN_URL)
    else:
        user.is_active = True
        user.save()
        user.profile.email_confirmed = True
        user.profile.save()
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)
        return redirect('exmo2010:index')


@csrf_protect
@never_cache
def login(request):
    if request.user.is_authenticated():
        return redirect('exmo2010:index')

    if request.method == "GET":
        form = LoginForm(initial={'username': request.GET.get('email')})
    elif request.method == "POST":
        if not request.session.test_cookie_worked():
            return TemplateResponse(request, 'cookies.html')
        else:
            request.session.delete_test_cookie()

        form = LoginForm(request.POST)
        if form.is_valid():
            auth_login(request, form.user)

            profile = form.user.profile

            # Set language preference if does not exist
            if not profile.language:
                language = get_language_from_request(request, check_path=True)
                profile.language = language
                profile.save()

            redirect_url = request.REQUEST.get(REDIRECT_FIELD_NAME, '')

            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_url, host=request.get_host()):
                redirect_url = settings.LOGIN_REDIRECT_URL

            return HttpResponseRedirect(redirect_url)

    request.session.set_test_cookie()
    return TemplateResponse(request, 'registration/login.html', {'form': form})


def logout(request):
    auth_logout(request)

    redirect_url = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
    # Security check -- don't allow redirection to a different host.
    if not is_safe_url(url=redirect_url, host=request.get_host()):
        redirect_url = reverse('exmo2010:index')

    return HttpResponseRedirect(redirect_url)


def auth_orguser(request):
    """
    If user with given GET parameter 'email' exists - redirect to login.
    Otherwise redirect to registration_form.
    TODO: add current user to the list of org representatives for given GET parameter 'code'.
    """
    if request.user.is_authenticated():
        return redirect('exmo2010:index')

    email = request.GET.get('email')
    if email and User.objects.filter(email=email).exists():
        return HttpResponseRedirect(reverse('exmo2010:auth_login') + '?' + request.GET.urlencode())

    return HttpResponseRedirect(reverse('exmo2010:registration_form') + '?' + request.GET.urlencode())


def csrf_failure(request, reason=""):
    """
    Вызывается при непрохождении джанговских тестов.
    Cross Site Request Forgery protection. Переписана для того,
    чтобы объясняла пользователю о выключенных cookies в браузере.
    """
    if reason == REASON_NO_CSRF_COOKIE:
        return TemplateResponse(request, 'cookies.html')
    else:
        t = Template(CSRF_FAILURE_TEMPLATE)
        c = Context({
            'DEBUG': settings.DEBUG,
            'reason': reason,
            'no_referer': reason == REASON_NO_REFERER
        })
        return HttpResponseForbidden(t.render(c), mimetype='text/html')
