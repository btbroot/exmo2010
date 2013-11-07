# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render_to_response
from django.template import RequestContext, Context, loader
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView
from livesettings import config_value
from bread_crumbs.views import breadcrumbs
from exmo2010.forms import FeedbackForm


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

    crumbs = ['Home']
    breadcrumbs(request, crumbs)
    title = _('Feedback')

    t = 'exmo2010/feedback.html'
    c = {
        'current_title': title,
        'title': title,
        'form': form,
        'success': success,
    }
    return render_to_response(t, c, context_instance=RequestContext(request))


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
        return {
            'current_title': _('Help'),
            'support_email': config_value('EmailServer', 'DEFAULT_SUPPORT_EMAIL')
        }


class AboutView(TemplateView):
    template_name = 'exmo2010/about.html'

    def get_context_data(self, **kwargs):
        return {
            'current_title': _('About')
        }


class OpenDataView(TemplateView):
    template_name = 'exmo2010/opendata.html'

    def get_context_data(self, **kwargs):
        return {
            'current_title': _('Open data')
        }
