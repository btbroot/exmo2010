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
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext, Context, Template
from django.utils.http import base36_to_int
from django.core.urlresolvers import reverse
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.views.csrf import CSRF_FAILRE_TEMPLATE
from django.middleware.csrf import REASON_NO_CSRF_COOKIE
from django.middleware.csrf import REASON_NO_COOKIE, REASON_NO_REFERER
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.contrib.auth import login, REDIRECT_FIELD_NAME
from django.contrib.auth.views import login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from registration.views import register
from exmo2010.custom_registration.forms import SetPasswordForm
from exmo2010.forms import OrgUserInfoForm


@never_cache
def password_reset_confirm(request, uidb36=None, token=None,
                   template_name='registration/password_reset_confirm.html',
                   token_generator=default_token_generator,
                   current_app=None, extra_context=None):
    """
    Переприсанная стандартная вьюха для смены пароля.
    Изменение - немедленный логин после установки нового пароля.
    """
    assert uidb36 is not None and token is not None # checked by URLconf
    post_reset_redirect = reverse('exmo2010:index')
    try:
        uid_int = base36_to_int(uidb36)
        user = User.objects.get(id=uid_int)
    except (ValueError, User.DoesNotExist):
        user = None

    if user is not None and token_generator.check_token(user, token):
        validlink = True
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                user.backend='django.contrib.auth.backends.ModelBackend'
                login(request, user)
                return HttpResponseRedirect(post_reset_redirect)
        else:
            form = SetPasswordForm(None)
    else:
        validlink = False
        form = None
    context = {
        'form': form,
        'validlink': validlink,
        }
    context.update(extra_context or {})
    return render_to_response(template_name, context,
        context_instance=RequestContext(request, current_app=current_app))


def reg_finish(request):
    """
    Страница ввода доп. данных представителем орг-ии
    по окончании регистрации.
    """
    if not request.user.is_authenticated():
        raise Http404
    profile = request.user.profile
    if not profile.is_organization:
        raise Http404
    if profile.position or profile.phone:
        raise Http404
    if request.method == "POST":
        form = OrgUserInfoForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            position = cd.get("position", "")
            profile.position = position
            phone = cd.get("phone", "")
            profile.phone = phone
            profile.save()
            return HttpResponseRedirect(reverse("exmo2010:index"))
    else:
        form = OrgUserInfoForm()
    return render_to_response('exmo2010/org_user_info.html',
        {"form": form,},
        context_instance=RequestContext(request))


def register_test_cookie(request, backend, success_url=None, form_class=None,
                         disallowed_url='registration_disallowed',
                         template_name='registration/registration_form.html',
                         extra_context=None):
    """
    Проверяет работу cookie и возвращает стандартную вью для регистрации.
    Или отправляет на страницу с ошибкой.
    """
    if request.method == 'POST':
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()
        else:
            return render_to_response('cookies.html', RequestContext(request))

    request.session.set_test_cookie()
    return register(request,
        backend,
        success_url, form_class,
        disallowed_url,
        template_name,
        extra_context)


def login_test_cookie(request, template_name='registration/login.html',
                       redirect_field_name=REDIRECT_FIELD_NAME,
                       authentication_form=AuthenticationForm,
                       current_app=None, extra_context=None):
    """
    Проверяет работу cookie и возвращает стандартную вью для логина.
    Тестовые cookies создаются в оригинальной auth_login.
    """
    if request.method == 'POST':
        if not request.session.test_cookie_worked():
            return render_to_response('cookies.html', RequestContext(request))

    return auth_login(request,
        template_name,
        redirect_field_name,
        authentication_form,
        current_app,
        extra_context)


def csrf_failure(request, reason=""):
    """
    Вызывается при непрохождении джанговских тестов.
    Cross Site Request Forgery protection. Переписана для того,
    чтобы объясняла пользователю о выключенных cookies в браузере.
    """
    if (reason == REASON_NO_COOKIE or
        reason == REASON_NO_CSRF_COOKIE):
        return render_to_response('cookies.html', RequestContext(request))
    else:
        t = Template(CSRF_FAILRE_TEMPLATE)
        c = Context({'DEBUG': settings.DEBUG,
                     'reason': reason,
                     'no_referer': reason == REASON_NO_REFERER
        })
        return HttpResponseForbidden(t.render(c), mimetype='text/html')