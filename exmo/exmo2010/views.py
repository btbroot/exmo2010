# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
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
from collections import OrderedDict
from urllib import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.formtools.wizard.views import SessionWizardView
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.template import Context, loader
from django.template.response import TemplateResponse
from django.utils import dateformat
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView
from livesettings import config_value

from core.tasks import send_email
from exmo2010.forms import FeedbackForm
from exmo2010.models import *


def feedback(request):
    success = False

    if request.user.is_active:
        form = FeedbackForm(initial={'email': request.user.email})
    else:
        form = FeedbackForm()

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            support_email = config_value('EmailServer', 'DEFAULT_SUPPORT_EMAIL'),
            email = form.cleaned_data['email']
            comment = form.cleaned_data['comment']
            if request.user.is_active:
                user = request.user
            else:
                user = None
            _send_feedback_mail(support_email,
                                [email, ],
                                comment,
                                "exmo2010/emails/feedback_recipient.txt",
                                "exmo2010/emails/feedback_recipient.html",
                                user=user)
            _send_feedback_mail([email, ],
                                [email, ],
                                comment,
                                "exmo2010/emails/feedback_creator.txt",
                                "exmo2010/emails/feedback_creator.html",
                                user=user)
            success = True

    context = {
        'title': _('Feedback'),
        'form': form,
        'success': success,
    }
    return TemplateResponse(request, 'exmo2010/feedback.html', context)


def _send_feedback_mail(email_to, email_from, comment, t_txt, t_html, user=None):
    subject = _("Feedback")
    t_txt = loader.get_template(t_txt)
    t_html = loader.get_template(t_html)
    c = Context({'comment': comment,
                 'email': email_from[0],
                 'user': user, })
    content_html = t_html.render(c)
    content_txt = t_txt.render(c)
    letter = EmailMultiAlternatives(subject,
                                    content_txt,
                                    config_value('EmailServer', 'DEFAULT_FROM_EMAIL'),
                                    email_to,
                                    [],
                                    {},)
    letter.attach_alternative(content_html, "text/html")
    letter.send()


class HelpView(TemplateView):
    template_name = 'exmo2010/help.html'

    def get_context_data(self, **kwargs):
        current_site = Site.objects.get_current()
        protocol = self.request.is_secure() and 'https' or 'http'

        registration_url = '%s://%s%s' % (
            protocol,
            current_site.domain,
            reverse('exmo2010:registration_register')
        )
        return {
            'support_email': config_value('EmailServer', 'DEFAULT_SUPPORT_EMAIL'),
            'registration_url': registration_url,
        }


class AboutView(TemplateView):
    template_name = 'exmo2010/about.html'


class OpenDataView(TemplateView):
    template_name = 'exmo2010/opendata.html'


class CertificateOrderView(SessionWizardView):
    template_names = ["certificate_order_form.html", "certificate_order_confirm.html"]

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if request.user.profile.is_organization and not request.user.is_superuser:
            return super(CertificateOrderView, self).dispatch(request, *args, **kwargs)

        return HttpResponseForbidden(_('Forbidden'))

    def get_form_initial(self, step):
        if self.steps.current == self.steps.first:
            initial_data = {
                'name': self.request.user.profile.legal_name,
                'email': self.request.user.email,
            }
            self.initial_dict.update({self.steps.current: initial_data})
        result = super(CertificateOrderView, self).get_form_initial(step)

        return result

    def get_context_data(self, form, **kwargs):
        context = super(CertificateOrderView, self).get_context_data(form=form, **kwargs)
        first_step = self.steps.first
        request = self.request
        rating_type = request.GET.get('type', 'all')

        if self.steps.current == first_step:
            context_data = {}
            organizations = request.user.profile.organization.filter(monitoring__status=MONITORING_PUBLISHED)
            tasks = Task.objects.filter(organization__in=organizations, status=Task.TASK_APPROVED)

            if tasks.exists():
                has_npa = organizations.filter(monitoring__parameter__npa=True)

                name_filter = request.GET.get('name_filter')
                if name_filter:
                    tasks = tasks.filter(organization__name__icontains=name_filter)
                    has_npa = has_npa.filter(name__icontains=name_filter)

                if rating_type in ['npa', 'other']:
                    tasks = tasks.filter(organization__monitoring__parameter__npa=True).distinct()

                object_list = OrderedDict()

                for task in tasks:
                    monitoring = task.organization.monitoring
                    rating_list = monitoring.rating(rating_type=rating_type)
                    place = {t.pk: t.place for t in rating_list}.get(task.pk, None)

                    object_list[task.pk] = {
                        'openness': task.openness,
                        'org_name': task.organization.name,
                        'place': place,
                        'publish_date': monitoring.publish_date,
                        'url': task.organization.url,
                    }

                context_data = {
                    'has_npa': has_npa,
                    'object_list': object_list,
                    'rating_type': rating_type,
                }

                self.storage.extra_data = {'object_list': object_list}

        else:
            by_type = {
                'all': _('by all'),
                'npa': _('by normative'),
                'other': _('by recommendatory'),
            }

            form_data = self.get_cleaned_data_for_step(first_step)
            task = self.storage.extra_data['object_list'].get(form_data['task_id'])

            description = _('For %(name)s organization, which took %(place)d place with %(openness).3f%% openness in '
                            'rating %(type)s parameters, which published %(date)s.') %\
                {
                    'name': task['org_name'],
                    'place': task['place'],
                    'openness': task['openness'],
                    'type': by_type[rating_type],
                    'date': dateformat.format(task['publish_date'], "j E Y"),
                }

            if form_data['delivery_method'] == "1":
                on_address = _('On address %(zip_code)s, %(address)s, %(for_whom)s.') % \
                    {
                        'zip_code': form_data['zip_code'],
                        'address': form_data['address'],
                        'for_whom': form_data['for_whom'],
                    }
            else:
                on_address = _('On email address %s.') % form_data['email']

            context_data = {
                'description': description,
                'on_address': on_address,
                'special_wishes': form_data['wishes'],
                'breadcrumbs': [{'url': reverse('exmo2010:index')},
                                {'url': reverse('exmo2010:certificate_order'), 'title': _('Openness certificate')},
                                {'title': _('Confirmation of a certificate ordering')}]
            }

            if form_data['certificate_for'] == "1":
                prepare_for = _('Prepare a certificate in the name of %s.') % form_data['name']
                context_data.update({'prepare_for': prepare_for})

        title = _('Openness certificate')

        if self.steps.current != first_step:
            self.storage.extra_data.update({'email_context': context_data})
            title = _('Confirmation of a certificate ordering')

        context_data.update({
            'title': title,
        })
        context.update(context_data)

        return context

    def get_template_names(self):
        return [self.template_names[self.steps.step0]]

    def done(self, form_list, **kwargs):
        request = self.request
        task_id = self.get_cleaned_data_for_step(self.steps.first)['task_id']
        task = Task.objects.get(pk=task_id)
        organization = task.organization
        organization_name = organization.name
        monitoring_name = organization.monitoring.name
        subject = ' '.join([_('Ordering openness certificate for'), organization_name])
        rcpt = config_value('EmailServer', 'CERTIFICATE_ORDER_NOTIFICATION_EMAIL')

        current_site = Site.objects.get_current()
        protocol = request.is_secure() and 'https' or 'http'

        monitoring_url = '%s://%s%s' % (
            protocol,
            current_site.domain,
            reverse('exmo2010:tasks_by_monitoring', args=[organization.monitoring.pk])
        )

        organization_url = '%s?%s' % (monitoring_url, urlencode({'filter0': organization.name}))

        context = {
            'email': request.user.email,
            'monitoring_name': monitoring_name,
            'monitoring_url': monitoring_url,
            'organization_name': organization_name,
            'organization_url': organization_url,
            'subject': subject,
            'user_name': request.user.profile.legal_name,
        }

        context.update(self.storage.extra_data['email_context'])

        send_email.delay(rcpt, subject, 'certificate_order_email', context=context)
        messages.success(request, _("You ordered an openness certificate. Certificate "
                                    "will be prepared and sent within 5 working days."))

        return HttpResponseRedirect(reverse('exmo2010:index'))
