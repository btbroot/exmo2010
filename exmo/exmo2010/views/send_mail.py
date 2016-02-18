# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2016 IRSI LTD
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
import json
from os.path import join, basename
from urllib import urlencode

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect
from django.template.defaultfilters import filesizeformat
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, UpdateView
from pytils.translit import translify


from core.response import JSONResponse
from core.views import LoginRequiredMixin
from exmo2010.mail import mail_organization, mail_orguser
from exmo2010.models import Monitoring, Organization, SentMailHistory, Score, UserProfile, OrgUser
from queryform import QueryForm


@login_required
def ajax_upload_file(request):
    max_upload_size = settings.EMAIL_ATTACHMENT_MAX_UPLOAD_SIZE
    if request.method == "POST" and request.is_ajax() and request.user.is_expertA:
        upload_file = request.FILES.get('upload_file')
        error = None
        if upload_file:
            # BUG #2369 restriction of file content type does not work. (Removed from code now)
            if upload_file._size > max_upload_size:
                error = _('Please keep file size under {max_size}. Current file size {size}.').format({
                    'max_size': filesizeformat(max_upload_size), 'size': filesizeformat(upload_file._size)})
        else:
            error = _('No file.')
        context = {'error': error}

        if not error:
            upload_path = settings.EMAIL_ATTACHMENT_UPLOAD_PATH
            upload_filename = default_storage.get_available_name(join(upload_path, translify(upload_file.name)))
            saved_path = default_storage.save(upload_filename, upload_file)
            context = {'saved_filename': basename(saved_path), 'original_filename': upload_file.name}

        return JSONResponse(context)

    raise PermissionDenied


class SendMailMixin(LoginRequiredMixin):
    pk_url_kwarg = 'monitoring_pk'
    context_object_name = 'monitoring'
    model = Monitoring

    def get_object(self, queryset=None):
        self.monitoring = super(SendMailMixin, self).get_object(queryset)
        if not self.request.user.has_perm('exmo2010.admin_monitoring', self.monitoring):
            raise PermissionDenied
        return self.monitoring


class SendMailView(SendMailMixin, UpdateView):
    template_name = "manage_monitoring/send_mail.html"

    def get_form_class(self):
        form = modelform_factory(SentMailHistory, exclude=('monitoring', 'inv_status'), widgets={'subject': forms.TextInput})
        form.base_fields.update({
            'attachments_names': forms.CharField(required=False, widget=forms.Textarea()),
            'handpicked_orgs': forms.ModelMultipleChoiceField(self.monitoring.organization_set, required=False)})
        return form

    def get_form_kwargs(self):
        kwargs = super(SendMailView, self).get_form_kwargs()
        kwargs.update({
            'instance': SentMailHistory(monitoring=self.monitoring),
            'initial': {'handpicked_orgs': self.request.GET.getlist('orgs')}})
        return kwargs

    def replace_link(self, text, email, orgs):
        params = {'code': [org.inv_code for org in orgs]}
        if email:
            params['email'] = email
        url = reverse('exmo2010:auth_orguser') + '?' + urlencode(params, True)
        return text.replace('%link%', self.request.build_absolute_uri(url))

    def form_valid(self, form):
        """
        Return first email preview instead of sending emails if request is AJAX.
        Send email messages to selected recipients, expanding magic words %code% and %link%.
        """
        preview_only = self.request.is_ajax()

        if not preview_only:
            self.object = form.save()
        formdata = form.cleaned_data

        attachments = []
        if not preview_only:
            attachments_names = formdata.get('attachments_names')

            if attachments_names:
                for saved_filename, original_filename in json.loads(attachments_names).items():
                    saved_file = default_storage.open(join(settings.EMAIL_ATTACHMENT_UPLOAD_PATH, saved_filename))
                    attachments.append((original_filename, saved_file.read()))
                    saved_file.close()

        # At first, send messages to organizations, selected with checkbox filters. If request is ajax - return
        # preview of message to the first matching organization.
        if formdata['handpicked_orgs']:
            prepicked_orgs = Organization.objects.filter(pk__in=formdata['handpicked_orgs'])
        else:
            prepicked_orgs = self.monitoring.organization_set.all()

        orgs = []
        if formdata.get('dst_orgs_noreg'):
            orgs += prepicked_orgs.filter(inv_status__in=['NTS', 'SNT', 'RD'])
        if formdata.get('dst_orgs_inact'):
            orgs += prepicked_orgs.filter(inv_status='RGS')
        if formdata.get('dst_orgs_activ'):
            orgs += prepicked_orgs.filter(inv_status='ACT')

        for org in orgs:
            comment_text = formdata['comment'].replace('%code%', org.inv_code)
            for addr in org.email_iter():
                text = self.replace_link(comment_text, addr, [org])
                if preview_only:
                    context = {'email': addr, 'subject': formdata['subject'], 'body': text}
                    return JSONResponse({'page': render_to_string('mail/email_preview.html', context)})
                else:
                    mail_organization(addr, org, formdata['subject'], text, attachments)

        # Secondly, send messages to org-users (representatives), selected with checkbox filters. If request is
        # ajax - return preview of message to the first matching user.
        orgusers = UserProfile.objects.filter(organization__monitoring=self.monitoring).prefetch_related('organization')
        if formdata['handpicked_orgs']:
            orgusers = orgusers.filter(organization__in=formdata['handpicked_orgs'])

        seen = OrgUser.objects.filter(organization__monitoring=self.monitoring, seen=True).values_list('userprofile_id', flat=True)

        scores = Score.objects.filter(parameter__monitoring=self.monitoring)
        orgusers_seen = orgusers.filter(pk__in=seen)
        orgusers_unseen = orgusers.exclude(pk__in=seen)
        active = orgusers_seen.filter(user__comment_comments__object_pk__in=scores).distinct()
        inactive = orgusers_seen.exclude(user__comment_comments__object_pk__in=scores).distinct()

        mailto = []
        if formdata.get('dst_orgusers_inact'):
            mailto += list(inactive)
        if formdata.get('dst_orgusers_activ'):
            mailto += list(active)
        if formdata.get('dst_orgusers_unseen'):
            mailto += list(orgusers_unseen)

        monitoring_orgs = set(self.monitoring.organization_set.all())

        for user in mailto:
            # All orgs of this user in this monitoring.
            user_orgs = filter(monitoring_orgs.__contains__, user.organization.all())

            if '%code%' in formdata['comment']:
                # Send email to this user for every related organization in this monitoring.
                comment_text = self.replace_link(formdata['comment'], user.user.email, user_orgs)
                texts = [comment_text.replace('%code%', org.inv_code) for org in user_orgs]
            elif '%link%' in formdata['comment']:
                # Send single email to this user with all related organizations in one link.
                texts = [self.replace_link(formdata['comment'], user.user.email, user_orgs)]
            else:
                # Send single email to this user without any magic words.
                texts = [formdata['comment']]

            for text in texts:
                if preview_only:
                    context = {'email': user.user.email, 'subject': formdata['subject'], 'body': text}
                    return JSONResponse({'page': render_to_string('mail/email_preview.html', context)})
                else:
                    mail_orguser(user.user.email, formdata['subject'], text, attachments)

        if preview_only:
            return JSONResponse({'error': True, 'page': _('This email will not be delivered to anyone!')})
        else:
            messages.success(self.request, _('Mails sent.'))
            url = reverse('exmo2010:send_mail_history', args=[self.monitoring.pk])

            return HttpResponseRedirect('%s?%s' % (url, self.request.GET.urlencode()))

    def form_invalid(self, form):
        if self.request.is_ajax():
            return JSONResponse({'error': True, 'page': _('Form error!')})
        else:
            return super(SendMailView, self).form_invalid(form)


class SentMailHistoryQueryForm(QueryForm):
    timestamp = forms.DateField(required=False, widget=forms.TextInput())

    class Meta:
        filters = {
            'timestamp': 'timestamp__gte',
        }


class SendMailHistoryView(SendMailMixin, DetailView):
    template_name = "manage_monitoring/send_mail_history.html"

    def get_context_data(self, **kwargs):
        context = super(SendMailHistoryView, self).get_context_data(**kwargs)
        mail_history = SentMailHistory.objects.filter(monitoring=self.object)
        is_mail_history_exist = mail_history.exists()

        self.queryform = SentMailHistoryQueryForm(self.request.GET)
        if self.queryform.is_valid():
            mail_history = self.queryform.apply(mail_history)

        context['mail_history'] = mail_history
        context['is_mail_history_exist'] = is_mail_history_exist

        return context
