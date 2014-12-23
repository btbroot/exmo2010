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
import re
from urllib import urlencode

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail.utils import DNS_NAME
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.template import loader, Context
from django.utils.translation import get_language, ugettext as _
from django.utils import translation
from livesettings import config_value

from custom_comments.models import CommentExmo
from .celery_tasks import send_email, send_org_email
from .models import UserProfile, Organization, MONITORING_INTERACTION, MONITORING_FINALIZING


class ExmoEmail(EmailMultiAlternatives):
    def __init__(self, *args, **kwargs):
        template_basename = kwargs.pop('template_basename')
        context = Context(dict(kwargs.pop('context'), subject=kwargs['subject']))

        body_txt = loader.get_template(template_basename + '.txt').render(context)
        body_html = loader.get_template(template_basename + '.html').render(context)

        kwargs.update(
            body=body_txt,
            alternatives=[(body_html, "text/html")],
            from_email=kwargs.get('from_email', config_value('EmailServer', 'DEFAULT_FROM_EMAIL')))

        super(ExmoEmail, self).__init__(*args, **kwargs)


_expertsA = Q(groups__name=UserProfile.expertA_group, is_active=True)


def _mail_claim(request, subject, claim, context):
    subject = '%(prefix)s%(monitoring)s - %(org)s: %(code)s - %(subject)s' % {
        'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
        'monitoring': claim.score.task.organization.monitoring,
        'org': claim.score.task.organization.name.split(':')[0],
        'code': claim.score.parameter.code,
        'subject': subject,
    }

    url = request.build_absolute_uri(reverse('exmo2010:score', args=[claim.score.pk]))
    context = dict(context, claim=claim, request=request, url=url)

    users = User.objects.filter(_expertsA | Q(pk=claim.addressee.pk)).distinct()

    for email, language in users.values_list('email', 'userprofile__language'):
        if email:
            with translation.override(language or settings.LANGUAGE_CODE):
                send_email.delay(ExmoEmail(template_basename='mail/score_claim',
                                           context=context, to=[email], subject=subject))


def mail_claim_new(request, claim):
    _mail_claim(request, _('New claim'), claim, {'created': True})


def mail_claim_deleted(request, claim):
    _mail_claim(request, _('Delete claim'), claim, {'created': False})


def mail_clarification(request, clarification):
    score = clarification.score

    subject = '%(prefix)s%(monitoring)s - %(org)s: %(code)s - %(subject)s' % {
        'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
        'monitoring': score.task.organization.monitoring,
        'org': score.task.organization.name.split(':')[0],
        'code': score.parameter.code,
        'subject': _('New clarification')
    }

    url = request.build_absolute_uri(reverse('exmo2010:score', args=[score.pk]))
    context = dict(score=score, clarification=clarification, url=url)

    users = User.objects.filter(_expertsA | Q(pk=score.task.user.pk)).distinct()

    for email, language in users.values_list('email', 'userprofile__language'):
        if email:
            with translation.override(language or settings.LANGUAGE_CODE):
                send_email.delay(ExmoEmail(template_basename='mail/score_clarification',
                                           context=context, to=[email], subject=subject))


def mail_organization(email, org, subject, body, attachments=None):
    message = ExmoEmail(
        template_basename='mail/email_base',
        context={'subject': subject, 'body': body},
        to=[email],
        subject=subject,
        attachments=attachments)

    match = re.search('([\w.-]+)@([\w.-]+)', message.from_email)
    extra_headers_email = match.group() if match else ''

    message.extra_headers = {
        'Disposition-Notification-To': extra_headers_email,
        'X-Confirm-Reading-To': extra_headers_email,
        'Return-Receipt-To': extra_headers_email,
        'Message-ID': '<%s@%s>' % (org.inv_code, DNS_NAME)}

    send_org_email.delay(message, org.pk)


def mail_orguser(email, subject, body, attachments=None):
    if not email:
        return

    message = ExmoEmail(
        template_basename='mail/email_base',
        context={'subject': subject, 'body': body},
        to=[email],
        subject=subject,
        attachments=attachments)

    send_email.delay(message)


def mail_certificate_order(request, email_data):
    org = email_data['organization']
    subject = '%s %s' % (_('Ordering openness certificate for'), org.name)

    url = reverse('exmo2010:tasks_by_monitoring', args=[org.monitoring.pk])
    monitoring_url = request.build_absolute_uri(url)

    organization_url = '%s?%s' % (monitoring_url, urlencode({'filter0': org.name.encode('utf8')}))

    context = dict(
        email_data,
        monitoring_url=monitoring_url,
        organization_url=organization_url,
        subject=subject,
        user=request.user,
    )

    to = config_value('EmailServer', 'CERTIFICATE_ORDER_NOTIFICATION_EMAIL')
    send_email.delay(ExmoEmail(template_basename='mail/certificate_order_email',
                               context=context, to=[to], subject=subject))


def mail_param_edited(param, form):
    fields = 'code name_{lang} grounds_{lang} rating_procedure_{lang} notes_{lang} weight'\
        .format(lang=get_language()).split()
    criteria = 'accessible hypertext npa topical document image complete'.split()

    old_excluded_org_pk = form.initial.get('exclude', form.fields['exclude'].initial)

    context = dict(
        monitoring=param.monitoring,
        old_features=[(f, form.initial.get(f, form.fields[f].initial)) for f in fields],
        new_features=[(f, getattr(param, f, None)) for f in fields],
        old_criteria=[c for c in criteria if form.initial.get(c, form.fields[c].initial)],
        new_criteria=[c for c in criteria if getattr(param, c, None)],
        old_excluded_org=Organization.objects.filter(pk__in=old_excluded_org_pk),
        new_excluded_org=param.exclude.all())

    subject = _('{subject_prefix}Parameter has been changed: {param}').format(
        subject_prefix=config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'), param=param.name)

    orgs = Organization.objects.filter(monitoring=param.monitoring).exclude(pk__in=param.exclude.all())

    orgusers = User.objects\
        .filter(task__organization__in=orgs, is_active=True, email__isnull=False)\
        .exclude(email__exact='')\
        .distinct()\
        .values_list('email', 'userprofile__language')

    expertsA = User.objects.filter(_expertsA).distinct().values_list('email', 'userprofile__language')

    for email, language in set(orgusers) | set(expertsA):
        if email:
            with translation.override(language or settings.LANGUAGE_CODE):
                send_email.delay(ExmoEmail(template_basename='mail/parameter_email',
                                           context=context, to=[email], subject=subject))


def mail_comment(request, comment):
    score = comment.content_object
    monitoring = score.task.organization.monitoring
    if not monitoring.status in [MONITORING_INTERACTION, MONITORING_FINALIZING]:
        return

    users = User.objects.filter(
        userprofile__notification_type=UserProfile.NOTIFICATION_ONEBYONE,
        is_active=True,
        email__isnull=False)
    users = users.exclude(pk=comment.user.pk, userprofile__notification_self=False)

    experts = users.filter(Q(is_superuser=True) | Q(groups__name=UserProfile.expertA_group) | Q(pk=score.task.user.pk))
    experts_thread = experts.filter(userprofile__notification_thread=True)
    experts_one = experts.filter(userprofile__notification_thread=False)

    orgusers = users.filter(userprofile__organization=score.task.organization)
    orgusers_thread = orgusers.filter(userprofile__notification_thread=True)
    orgusers_one = orgusers.filter(userprofile__notification_thread=False)

    subject = u'%(prefix)s%(monitoring)s - %(org)s: %(code)s' % {
        'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
        'monitoring': monitoring,
        'org': score.task.organization.name.split(':')[0],
        'code': score.parameter.code}

    context = {
        'title': '%s: %s' % (score.task.organization, score.parameter),
        'masked_expert_name': _(config_value('GlobalParameters', 'EXPERT'))}

    comment_url = request.build_absolute_uri(reverse('exmo2010:score', args=[score.pk])) + '#c%s' % comment.pk
    recommendation_url = request.build_absolute_uri(reverse('exmo2010:recommendations', args=[score.task.pk])) + \
        '#param%s' % score.parameter.pk

    # Send notifications with single comment.
    _mail_comment(experts_one, subject, dict(context, comments=[comment], url=comment_url, mask_expert_name=False))
    _mail_comment(orgusers_one, subject, dict(context, comments=[comment], url=recommendation_url, mask_expert_name=True))

    thread = CommentExmo.objects.filter(object_pk=score.pk)

    # Send notifications with whole comments thread.
    _mail_comment(experts_thread, subject, dict(context, comments=thread, url=comment_url, mask_expert_name=False))
    _mail_comment(orgusers_thread, subject, dict(context, comments=thread, url=recommendation_url, mask_expert_name=True))


def _mail_comment(rcpts, subject, context):
    for email, language in rcpts.distinct().values_list('email', 'userprofile__language'):
        if email:
            with translation.override(language or settings.LANGUAGE_CODE):
                message = ExmoEmail(template_basename='mail/score_comment', context=context, subject=subject, to=[email])
                send_email.delay(message)


def mail_task_assigned(task):
    """
    Notifies assigned expert about her new task
    """
    if not task.user.email:
        return
    subject = _('You have an assigned task')
    url = reverse('exmo2010:task_scores', args=[task.pk])
    context = dict(task=task, subject=subject, url='http://%s%s' % (Site.objects.get_current(), url))

    with translation.override(task.user.profile.language or settings.LANGUAGE_CODE):
        message = ExmoEmail(template_basename='mail/task_user_assigned',
                            context=context, subject=subject, to=[task.user.email])
        send_email.delay(message)


def mail_feedback(request, sender_email, body):
    # Send email back to author
    send_email.delay(ExmoEmail(
        template_basename='mail/feedback_creator',
        context={'comment': body},
        subject=_("Feedback"),
        to=[sender_email]))

    # Send email to support staff
    send_email.delay(ExmoEmail(
        template_basename='mail/feedback_recipient',
        context=dict(comment=body, email=sender_email, user=request.user),
        subject=_("Feedback"),
        to=[config_value('EmailServer', 'DEFAULT_SUPPORT_EMAIL')]))


def mail_password_reset(request, user, reset_url):
    send_email.delay(ExmoEmail(
        template_basename='mail/password_reset_email',
        subject=_('Password reset on %s') % request.get_host(),
        context={'url': request.build_absolute_uri(reset_url)},
        to=[user.email]))


def mail_register_activation(request, user, activation_url):
    subject = _('Registration on %s') % request.get_host()

    context = {
        'activation_url': request.build_absolute_uri(activation_url),
        'login_url': request.build_absolute_uri(unicode(settings.LOGIN_URL)),
    }

    send_email.delay(ExmoEmail(template_basename='mail/activation_email',
                               context=context, subject=subject, to=[user.email]))
