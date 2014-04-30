# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
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
from collections import OrderedDict

from django import http
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template import RequestContext, loader
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils import dateformat, translation
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import requires_csrf_token
from django.views.generic import TemplateView, DetailView, FormView
from django.views.i18n import set_language
from livesettings import config_value

from .mail import mail_certificate_order, mail_feedback
from exmo2010.forms import FeedbackForm, CertificateOrderForm
from exmo2010.models import Monitoring, MONITORING_PUBLISHED, Task, StaticPage, LicenseTextFragments


def feedback(request):
    success = False

    if request.user.is_active:
        form = FeedbackForm(initial={'email': request.user.email})
    else:
        form = FeedbackForm()

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            mail_feedback(request, form.cleaned_data['email'], form.cleaned_data['comment'])
            success = True

    context = {
        'title': _('Feedback'),
        'form': form,
        'success': success,
    }
    return TemplateResponse(request, 'exmo2010/feedback.html', context)



class StaticPageView(DetailView):
    template_name = 'exmo2010/static_page.html'

    def get_object(self):
        """ Create static page if it does not exist yet. Fill in default content_en if empty. """
        page, created = StaticPage.objects.get_or_create(pk=self.static_page_pk)
        if not page.content_en:
            with translation.override('en'):
                page.content_en = render_to_string(self.default_content, self.get_default_context())
            page.save()
        return page

    def get_default_context(self):
        """ Override this method to pass custom context when default content is rendered. """
        return {}


class HelpView(StaticPageView):
    static_page_pk = 'help'
    default_content = 'exmo2010/static_pages/help.html'

    def get_default_context(self):
        return {
            'support_email': config_value('EmailServer', 'DEFAULT_SUPPORT_EMAIL'),
            'registration_url': self.request.build_absolute_uri(reverse('exmo2010:registration_register'))
        }


class AboutView(StaticPageView):
    static_page_pk = 'about'
    default_content = 'exmo2010/static_pages/about.html'


class OpenDataView(TemplateView):
    template_name = 'exmo2010/opendata.html'

    def get_context_data(self, **kwargs):
        context = super(OpenDataView, self).get_context_data(**kwargs)
        license = LicenseTextFragments.objects.filter(pk='license')
        json_license = license[0].json_license if license else {}
        context['json_license'] = json_license
        return context


class CertificateOrderView(FormView):
    template_name = "certificate_order_form.html"
    form_class = CertificateOrderForm

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_organization:
            raise PermissionDenied
        return super(CertificateOrderView, self).dispatch(request, *args, **kwargs)

    def get_form(self, form_class):
        form = super(CertificateOrderView, self).get_form(form_class)
        self.rating_type = form['rating_type'].value()

        orgs = self.request.user.profile.organization.filter(monitoring__status=MONITORING_PUBLISHED)
        _tasks = Task.objects.filter(organization__in=orgs, status=Task.TASK_APPROVED)
        if not _tasks.exists():
            # User don't have published and approved tasks, certificate order is unavailable
            self.template_name = "certificate_order_unavailable.html"
            return None

        # Check if rating_type filter should be displayed
        pks = Monitoring.objects.filter(organization__in=orgs).values_list('pk', flat=True)
        if set(pks.filter(parameter__npa=True).distinct()) & set(pks.filter(parameter__npa=False).distinct()):
            # There is Monitoring with both npa and non-npa parameters
            self.vary_rating_type = True
        else:
            self.vary_rating_type = False

        # Apply user provided filters
        if self.request.GET.get('name_filter'):
            orgs = orgs.filter(name__icontains=self.request.GET['name_filter'])

        _org_pks = set(orgs.values_list('pk', flat=True))
        _filter = {'organization__in': _org_pks}

        if self.rating_type in ['npa', 'other']:
            # NOTE: This logic works only because currently there are only 3 types of monitoring:
            # 1) Monitoring with both npa and non-npa parameters.
            # 2) Monitoring with only npa parameters.
            # 3) Monitoring with only non-npa parameters in DB, but really it does not differentiate parameters
            #    and should only be visible when "all" rating type chosen.
            # Therefore if "non-npa" ("other") rating chosen - we can first select all monitorings that have npa parameter.
            # Then caluclate "non-npa" rating. Resulting rated tasks list will be empty if there are only npa
            # parameters in monitoring (see Monitoring.rating). As a result only organizations from
            # monitorings with both npa and non-npa parameters (case 1) will be displayed
            #
            # This logic will break when real monitoring with all-non-npa parameters will be introduced.
            # It should be visible when "non-npa" rating is chosen, but filter below will exclude it :(
            _filter['parameter__npa'] = True

        # Build rated tasks ordered dict to display
        self.tasks = OrderedDict()
        for monitoring in Monitoring.objects.filter(**_filter).select_related('openness_expression')\
                                            .distinct().order_by('-publish_date'):
            for t in monitoring.rating(rating_type=self.rating_type):
                if t.organization.pk in _org_pks:
                    self.tasks[t.pk] = t

        return form

    def form_valid(self, form):
        if 'back' in self.request.POST:
            return self.render_to_response(self.get_context_data(form=form))

        email_data = self.prerender_email_text(form.cleaned_data)

        if 'confirm' in self.request.POST:
            mail_certificate_order(self.request, email_data)
            msg = _("You ordered an openness certificate. Certificate will be prepared and sent within 5 working days.")
            messages.success(self.request, msg)
            return HttpResponseRedirect(reverse('exmo2010:index'))
        else:
            return self.render_to_response(self.get_context_data(form=form, form_hidden='hidden', **email_data))

    def get_initial(self):
        return {
            'name': self.request.user.profile.legal_name,
            'email': self.request.user.email,
            'rating_type': self.request.REQUEST.get('rating_type', 'all'),
        }

    def prerender_email_text(self, form_data):
        rating_type_text = {'all': _('by all'), 'npa': _('by normative'), 'other': _('by recommendatory')}
        task = self.tasks[form_data['task_id']]

        #xgettext:no-python-format
        description = _('For {task.organization.name} organization, which took '
                        '{task.place} place with {task.task_openness:.3f}% openness'
                        ' in rating {rating_type} parameters, which published {date}.').format(
            task=task,
            rating_type=rating_type_text[form_data['rating_type']],
            date=dateformat.format(task.organization.monitoring.publish_date, "j E Y"))

        if form_data['delivery_method'] == "post":
            on_address = _('On address {zip_code}, {address}, {addressee}.').format(**form_data)
        else:
            on_address = _('On email address %s.') % form_data['email']

        email_data = {
            'organization': task.organization,
            'description': description,
            'on_address': on_address,
            'special_wishes': form_data['wishes']
        }

        if form_data['addressee'] == "user":
            prepare_for = _('Prepare a certificate in the name of %s.') % form_data['name']
            email_data.update({'prepare_for': prepare_for})

        return email_data


def change_language(request):
    """
    Change user profile language.

    """
    response = set_language(request)
    user = request.user
    if user.is_authenticated() and request.method == 'POST':
        language_code = request.POST.get('language', None)
        user.profile.language = language_code
        user.profile.save()

    return response


@requires_csrf_token
def server_error(request, template_name='500.html'):
    """
    Custom 500 error handler. Puts request in context.

    """
    t = loader.get_template(template_name)
    return http.HttpResponseServerError(t.render(RequestContext(request)))
