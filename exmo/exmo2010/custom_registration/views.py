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
from urllib import urlencode

from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout, REDIRECT_FIELD_NAME, authenticate
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from django.forms.fields import Field
from django.http import HttpResponseForbidden, HttpResponseNotAllowed, HttpResponseRedirect
from django.middleware.csrf import REASON_NO_CSRF_COOKIE, REASON_NO_REFERER
from django.shortcuts import redirect
from django.template import Context, Template
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.utils.translation import get_language_from_request
from django.views.csrf import CSRF_FAILURE_TEMPLATE
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from . import tokens
from .forms import LoginForm, RegistrationForm, ExistingEmailForm, SetPasswordForm
from exmo2010.mail import mail_register_activation, mail_password_reset
from exmo2010.models import Monitoring, Organization, Task, UserProfile


@csrf_protect
def password_reset_request(request, **kwargs):
    # TODO: Rate limit sending email to prevent flooding from our address.
    if request.method not in ['POST', 'GET']:
        return HttpResponseNotAllowed(permitted_methods=['POST', 'GET'])

    if request.user.is_authenticated():
        return redirect('exmo2010:index')

    codes = request.GET.getlist('code', [])
    orgs = Organization.objects.filter(inv_code__in=codes) if codes else []

    if request.method == "GET":
        form = ExistingEmailForm(initial={'email': request.GET.get('email')})
    else:  # POST
        form = ExistingEmailForm(request.POST)
        if form.is_valid():
            user = User.objects.get(email__iexact=form.cleaned_data["email"])
            token = tokens.PasswordResetTokenGenerator().make_token(user)
            url = reverse('exmo2010:password_reset_confirm', args=(user.pk, token))
            if request.GET:
                inv_codes = request.GET.getlist('code', [])
                params = {'code': inv_codes}
                url += '?{}'.format(urlencode(params, True))
            mail_password_reset(request, user, url)
            return redirect('{}?{}'.format(reverse('exmo2010:password_reset_sent'),
                                           urlencode({'email': form.cleaned_data['email']})))
    data = {'form': form, 'orgs': orgs, 'required_error': Field.default_error_messages['required'],
            'monitorings': Monitoring.objects.filter(organization__in=orgs).distinct()}

    return TemplateResponse(request, 'registration/password_reset_request.html', data)


@never_cache
def password_reset_confirm(request, user_pk, token):
    if request.method not in ['POST', 'GET']:
        return HttpResponseNotAllowed(permitted_methods=['POST', 'GET'])

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        user = None

    token_generator = tokens.PasswordResetTokenGenerator()
    if user is None or not token_generator.check_token(user, token):
        return TemplateResponse(request, 'registration/password_reset_confirm.html', {'link_invalid': True})

    codes = request.GET.getlist('code', [])
    orgs = Organization.objects.filter(inv_code__in=codes) if codes else []

    if request.method == 'GET':
        form = SetPasswordForm()
    else:  # POST
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            # We have to call authenticate() to properly annotate user authentication backend before login
            user = authenticate(username=user.username, password=form.cleaned_data['new_password'])
            auth_login(request, user)

            if orgs and not user.is_expert:
                return set_orguser_perms_and_redirect(user, orgs)

            return HttpResponseRedirect(reverse('exmo2010:index'))

    return TemplateResponse(request, 'registration/password_reset_confirm.html', {'form': form})


def registration_form(request):
    if request.method not in ['POST', 'GET']:
        return HttpResponseNotAllowed(permitted_methods=['POST', 'GET'])

    codes = request.GET.getlist('code', [])
    orgs = Organization.objects.filter(inv_code__in=codes) if codes else []

    if request.method == 'GET':
        form = RegistrationForm(initial={'email': request.GET.get('email'), 'invitation_code': ','.join(codes)})
    else:  # POST
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
        else:
            return TemplateResponse(request, 'cookies.html')

        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(request)
            for org in orgs:
                if user.email in org.email:
                    # User email match org email, activate him immediately.
                    user.is_active = True
                    user.save()
                    user.profile.email_confirmed = True
                    user.profile.save()
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    auth_login(request, user)

                    return set_orguser_perms_and_redirect(user, orgs)
            else:
                # User email does not match any org email, send him activation email message.
                token = tokens.EmailConfirmTokenGenerator().make_token(user)
                url = reverse('exmo2010:confirm_email', args=(user.pk, token))
                inv_codes = form.cleaned_data['invitation_code']
                if inv_codes:
                    params = {'code': inv_codes}
                    url += '?{}'.format(urlencode(params, True))
                mail_register_activation(request, user, url)

                return redirect('{}?{}'.format(reverse('exmo2010:please_confirm_email'),
                                               urlencode({'email': form.cleaned_data['email']})))

    request.session.set_test_cookie()
    data = {'form': form, 'orgs': orgs, 'monitorings': Monitoring.objects.filter(organization__in=orgs).distinct()}

    return TemplateResponse(request, 'registration/registration_form.html', data)


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
            return redirect('{}?{}'.format(reverse('exmo2010:please_confirm_email'),
                                           urlencode({'email': form.cleaned_data['email']})))

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
        codes = request.GET.getlist('code', [])
        orgs = Organization.objects.filter(inv_code__in=codes) if codes else []

        user.is_active = True
        user.save()
        user.profile.email_confirmed = True
        user.profile.save()
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)

        return set_orguser_perms_and_redirect(user, orgs)


@csrf_protect
@never_cache
def login(request):
    if request.method not in ['POST', 'GET']:
        return HttpResponseNotAllowed(permitted_methods=['POST', 'GET'])

    if request.user.is_authenticated():
        return redirect('exmo2010:index')

    codes = request.GET.getlist('code', [])
    orgs = Organization.objects.filter(inv_code__in=codes) if codes else []

    if request.method == 'GET':
        form = LoginForm(initial={'username': request.GET.get('email')}, getparams=request.GET.urlencode())
    else:  # POST
        if not request.session.test_cookie_worked():
            return TemplateResponse(request, 'cookies.html')
        else:
            request.session.delete_test_cookie()

        form = LoginForm(request.POST, getparams=request.GET.urlencode())
        if form.is_valid():
            user = form.user
            auth_login(request, user)

            # Set language preference if does not exist
            if not user.profile.language:
                language = get_language_from_request(request, check_path=True)
                user.profile.language = language
                user.profile.save()

            if orgs and not user.is_expert:
                return set_orguser_perms_and_redirect(user, orgs)

            redirect_url = request.REQUEST.get(REDIRECT_FIELD_NAME, '')

            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_url, host=request.get_host()):
                redirect_url = settings.LOGIN_REDIRECT_URL

            return HttpResponseRedirect(redirect_url)

    request.session.set_test_cookie()
    data = {'form': form, 'orgs': orgs, 'monitorings': Monitoring.objects.filter(organization__in=orgs).distinct()}

    return TemplateResponse(request, 'registration/login.html', data)


def logout(request):
    auth_logout(request)

    redirect_url = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
    # Security check -- don't allow redirection to a different host.
    if not is_safe_url(url=redirect_url, host=request.get_host()):
        redirect_url = reverse('exmo2010:index')

    return HttpResponseRedirect(redirect_url)


def auth_orguser(request):
    """
    If authenticated user is not expert with given GET parameter 'code' -
    set organization representatives permissions to user and redirect to recommendations page.
    Otherwise redirect to index page.

    If anonymous with given GET parameter 'email' exists - redirect to login.
    Otherwise redirect to registration_form.
    """
    if request.user.is_authenticated():
        if not request.user.is_expert:
            codes = request.GET.getlist('code', [])
            orgs = Organization.objects.filter(inv_code__in=codes) if codes else []
            return set_orguser_perms_and_redirect(request.user, orgs)

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


def set_orguser_perms_and_redirect(user, orgs):
    """
    Set organization representatives permissions to user and redirect to recommendations page
    if this page is available and if the count of organizations equals one.
    Otherwise redirect to index page.
    """
    if orgs:
        user.profile.organization.add(*orgs)
        if not user.profile.is_organization:
            org_group = Group.objects.get(name=UserProfile.organization_group)
            user.groups.add(org_group)

        if len(orgs) == 1:
            tasks = Task.objects.filter(organization=orgs[0], status=Task.TASK_APPROVED)
            if tasks.count() == 1 and user.has_perm('exmo2010.view_task', tasks[0]):
                return redirect('exmo2010:recommendations', task_pk=tasks[0].pk)

    return redirect('exmo2010:index')
