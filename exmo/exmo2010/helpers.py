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

"""
Модуль помощников для всего проекта в целом
"""

from datetime import timedelta, datetime
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.template import loader, Context
from django.utils.translation import ugettext as _
from django.utils.text import get_text_list
from django.db import IntegrityError
from django.db.models import Count
from reversion import revision
from exmo2010.models import UserProfile, Score, Task
from exmo2010.models import MonitoringInteractActivity, Organization
from exmo2010.utils import disable_for_loaddata


def construct_change_message(request, form, formsets):
        """
        Construct a change message from a changed object.
        Можно использовать для reversion
        """
        change_message = []
        if form.changed_data:
            change_message.append(_('Changed %s.') % get_text_list(form.changed_data, _('and')))

        if formsets:
            for formset in formsets:
                for added_object in formset.new_objects:
                    change_message.append(_('Added %(name)s "%(object)s".')
                                          % {'name': force_unicode(added_object._meta.verbose_name),
                                             'object': force_unicode(added_object)})
                for changed_object, changed_fields in formset.changed_objects:
                    change_message.append(_('Changed %(list)s for %(name)s "%(object)s".')
                                          % {'list': get_text_list(changed_fields, _('and')),
                                             'name': force_unicode(changed_object._meta.verbose_name),
                                             'object': force_unicode(changed_object)})
                for deleted_object in formset.deleted_objects:
                    change_message.append(_('Deleted %(name)s "%(object)s".')
                                          % {'name': force_unicode(deleted_object._meta.verbose_name),
                                             'object': force_unicode(deleted_object)})
        change_message = ' '.join(change_message)
        return change_message or _('No fields changed.')


def _get_experts():
    """
    Возвращает пользователей из групп expertA и expertB_manager
    """
    return User.objects.filter(
           groups__name__in=[UserProfile.expertA_group,
                             UserProfile.expertB_manager_group],
                            is_active=True,
                            email__isnull=False,
           ).exclude(email__exact='').distinct()


def comment_notification(sender, **kwargs):
    """
    Оповещение о комментариях
    """

    comment = kwargs['comment']
    request = kwargs['request']
    score = comment.content_object

    # Update user.email
    if not comment.user.email and comment.user_email:
        comment.user.email = comment.user_email
        comment.user.save()

    subject = u'%(prefix)s%(monitoring)s - %(org)s: %(code)s' % {
            'prefix': settings.EMAIL_SUBJECT_PREFIX,
            'monitoring': score.task.organization.monitoring,
            'org': score.task.organization.name.split(':')[0],
            'code': score.parameter.code,
            }
    admin_rcpt = []
    nonadmin_rcpt = []

    headers = {
        'X-iifd-exmo': 'comment_notification',
        'X-iifd-exmo-comment-organization-url': score.task.organization.url,
    }

    if comment.user.profile.notify_comment_preference['self']:
        admin_users = [comment.user,]
    else:
        admin_users = []

    # experts A, experts B managers
    if _get_experts(): admin_users.extend(_get_experts())

    # experts B
    if score.task.user.is_active: admin_users.extend([score.task.user,])

    for user in admin_users:
        if user.is_active and user.email and \
           user.profile.notify_comment_preference['type'] == \
           UserProfile.NOTIFICATION_TYPE_ONEBYONE:
            admin_rcpt.append(user.email)

    # Get only unique emails
    admin_rcpt=list(set(admin_rcpt))

    # Organizations
    nonadmin_users = User.objects.filter(
        userprofile__organization = score.task.organization,
        email__isnull = False,
    ).exclude(email__exact='').distinct('email')

    for user in nonadmin_users:
        if user.email and user.email not in admin_rcpt and \
           user.profile.notify_comment_preference['type'] == \
           UserProfile.NOTIFICATION_TYPE_ONEBYONE:
            nonadmin_rcpt.append(user.email)

    # Get only unique emails
    nonadmin_rcpt=list(set(nonadmin_rcpt))

    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http',
                         request.get_host(),
                         reverse('exmo2010:score_view',
                             args=[score.pk]))

    t_plain = loader.get_template('exmo2010/emails/score_comment.txt')
    t_html = loader.get_template('exmo2010/emails/score_comment.html')
    c = Context({'score': score,
                 'user': comment.user,
                 'admin': False,
                 'comment':comment,
                 'url': url,})
    message_plain = t_plain.render(c)
    message_html = t_html.render(c)

    for rcpt_ in nonadmin_rcpt:
        if  rcpt_ == comment.user.email:
            headers['X-iifd-exmo-comment-self'] = 'True'
        email = EmailMultiAlternatives(subject,
                                       message_plain,
                                       settings.DEFAULT_FROM_EMAIL,
                                       [rcpt_],
                                       [],
                                       headers=headers,)
        email.attach_alternative(message_html, "text/html")
        email.send()

    t_plain = loader.get_template('exmo2010/emails/score_comment.txt')
    t_html = loader.get_template('exmo2010/emails/score_comment.html')
    c = Context({'score': comment.content_object,
                 'user': comment.user,
                 'admin': True,
                 'comment':comment,
                 'url': url })
    message_admin_plain = t_plain.render(c)
    message_admin_html = t_html.render(c)
    for rcpt_ in admin_rcpt:
        if  rcpt_ == comment.user.email:
            headers['X-iifd-exmo-comment-self'] = 'True'
        email = EmailMultiAlternatives(subject,
                                       message_admin_plain,
                                       settings.DEFAULT_FROM_EMAIL,
                                       [rcpt_],
                                       [],
                                       headers=headers,)
        email.attach_alternative(message_admin_html, "text/html")
        email.send()


def comment_change_status(sender, **kwargs):
    """
    Изменение статуса предыдущего комментария после его сохранения
    """
    from custom_comments.models import CommentExmo
    comment = kwargs['comment']

    if comment.content_type.model == 'score':
        score = Score.objects.get(pk=comment.object_pk)

        previous_comments = CommentExmo.objects.filter(
            object_pk=score.pk).exclude(pk=comment.pk).order_by('-submit_date')

        if comment.user.profile.is_expert:
            for c in previous_comments:
                if c.user.profile.is_organization and \
                   c.status == CommentExmo.OPEN:
                    c.status = CommentExmo.ANSWERED
                    c.save()
                elif c.user.profile.is_expert:
                    break


def claim_notification(sender, **kwargs):
    """
    Оповещение о претензиях
    """

    claim = kwargs['claim']
    request = kwargs['request']
    score = claim.score

    subject = _('%(prefix)s%(monitoring)s - %(org)s: %(code)s - New claim') % {
            'prefix': settings.EMAIL_SUBJECT_PREFIX,
            'monitoring': score.task.organization.monitoring,
            'org': score.task.organization.name.split(':')[0],
            'code': score.parameter.code,
            }

    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http',
                         request.get_host(),
                         reverse('exmo2010:score_view',
                                 args=[score.pk]))

    t_plain = loader.get_template('exmo2010/emails/score_claim.txt')
    t_html = loader.get_template('exmo2010/emails/score_claim.html')

    c = Context({'score': score,
                 'claim': claim,
                 'url': url,})

    message_plain = t_plain.render(c)
    message_html = t_html.render(c)

    headers = {
        'X-iifd-exmo': 'claim_notification'
    }

    recipients = list(_get_experts().values_list('email', flat=True))

    if score.task.user.email and score.task.user.email not in recipients:
        recipients.append(score.task.user.email)

    for r in recipients:
        email = EmailMultiAlternatives(subject,
                                       message_plain,
                                       settings.DEFAULT_FROM_EMAIL,
                                       [r],
                                       [],
                                       headers=headers,)
        email.attach_alternative(message_html, "text/html")
        email.send()


def clarification_notification(sender, **kwargs):
    """
    Оповещение о претензиях
    """
    clarification = kwargs['clarification']
    request = kwargs['request']
    score = clarification.score

    subject = _(
        '%(prefix)s%(monitoring)s - %(org)s: %(code)s - New clarification'
    ) % {
        'prefix': settings.EMAIL_SUBJECT_PREFIX,
        'monitoring': score.task.organization.monitoring,
        'org': score.task.organization.name.split(':')[0],
        'code': score.parameter.code,
        }

    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http',
                         request.get_host(),
                         reverse('exmo2010:score_view',
                             args=[score.pk]))

    t_plain = loader.get_template('exmo2010/emails/score_clarification.txt')
    t_html = loader.get_template('exmo2010/emails/score_clarification.html')

    c = Context({'score': score,
                 'clarification': clarification,
                 'url': url,})

    message_plain = t_plain.render(c)
    message_html = t_html.render(c)

    headers = {
        'X-iifd-exmo': 'clarification_notification'
    }

    recipients = list(_get_experts().values_list('email', flat=True))

    if score.task.user.email and score.task.user.email not in recipients:
        recipients.append(score.task.user.email)

    for r in recipients:
        email = EmailMultiAlternatives(subject,
            message_plain,
            settings.DEFAULT_FROM_EMAIL,
            [r],
            [],
            headers=headers,)
        email.attach_alternative(message_html, "text/html")
        email.send()


@disable_for_loaddata
def post_save_model(sender, instance, created, **kwargs):
    """
    Функция для тригера post-save-model
    Сейчас нужна лишь для сохранения openness_first
    """

    must_register = False
    if revision.is_registered(instance.__class__):
        revision.unregister(instance.__class__)
        must_register = True
    #update task openness hook
    from exmo2010 import models
    if instance.__class__ == models.Monitoring:
        for task in models.Task.objects.filter(organization__monitoring = instance): task.update_openness()
    if must_register:
        revision.register(instance.__class__)


def create_profile(sender, instance, created, **kwargs):
    """
    post-save для модели User для создания профиля
    """

    if created:
        from exmo2010 import models
        profile = models.UserProfile(user = instance)
        profile.save()


def create_revision(sender, instance, using, **kwargs):
    """
    Сохранение ревизии оценки на стадии взаимодействия
    """

    if instance.revision != Score.REVISION_INTERACT:
        instance.create_revision(Score.REVISION_INTERACT)


def score_change_notify(sender, **kwargs):
    """
    Оповещение об измененях оценки
    """

    form = kwargs['form']
    score = form.instance
    request = kwargs['request']
    changes = []
    if form.changed_data:
        for change in form.changed_data:
            change_dict = {'field': change, 'was': form.initial.get(change, form.fields[change].initial), 'now': form.cleaned_data[change]}
            changes.append(change_dict)
    if score.task.approved:
        from exmo2010 import models
        rcpt = []
        for profile in models.UserProfile.objects.filter(organization = score.task.organization):
            if profile.user.is_active and profile.user.email and profile.notify_score_preference['type'] == UserProfile.NOTIFICATION_TYPE_ONEBYONE:
                rcpt.append(profile.user.email)
        rcpt = list(set(rcpt))
        subject = _('%(prefix)s%(monitoring)s - %(org)s: %(code)s - Score changed') % {
            'prefix': settings.EMAIL_SUBJECT_PREFIX,
            'monitoring': score.task.organization.monitoring,
            'org': score.task.organization.name.split(':')[0],
            'code': score.parameter.code,
        }
        headers = {
            'X-iifd-exmo': 'score_changed_notification'
        }
        url = '%s://%s%s' % (request.is_secure() and 'https' or 'http', request.get_host(), reverse('exmo2010:score_view', args=[score.pk]))
        t = loader.get_template('exmo2010/score_email.html')
        c = Context({ 'score': score, 'url': url, 'changes': changes, })
        message = t.render(c)
        for rcpt_ in rcpt:
            email = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [rcpt_], [], headers = headers)
            email.send()


def log_monitoring_interact_activity(monitoring, user):
    """
    Функция для ведения журнала посещений представителя организации
     на стадии взаимодействия
    """
    if (monitoring.is_interact and user.profile.is_organization
            and not user.is_superuser):
        if not MonitoringInteractActivity.objects.filter(monitoring=monitoring,
                                                         user=user).exists():
            log = MonitoringInteractActivity(monitoring=monitoring, user=user)
            try:
                log.save()
            except IntegrityError:
                pass

def comment_report(monitoring):
    """
    Вернет словарь с основной статистикой по комментариям
    """
    from custom_comments.models import CommentExmo

    result = {}
    comments_without_reply = []
    fail_comments_without_reply = []
    fail_soon_comments_without_reply = []
    fail_comments_with_reply = []
    active_organization_stats = []
    total_org = Organization.objects.filter(monitoring=monitoring)
    reg_org = total_org.filter(userprofile__isnull=False)
    start_date = monitoring.interact_date
    end_date = datetime.today()
    time_to_answer = monitoring.time_to_answer

    scores = Score.objects.filter(
        task__organization__monitoring=monitoring)

    iifd_all_comments = CommentExmo.objects.filter(
        content_type__model='score',
        submit_date__gte=start_date,
        object_pk__in=scores,
        user__in=User.objects.exclude(
            groups__name='organizations')).order_by('submit_date')

    org_all_comments = CommentExmo.objects.filter(
        content_type__model='score',
        submit_date__gte=start_date,
        object_pk__in=scores,
        user__in=User.objects.filter(
            groups__name='organizations')).order_by('submit_date')

    org_comments = org_all_comments.filter(
        status=CommentExmo.OPEN
    )

    comments_with_reply = org_all_comments.filter(
        status=CommentExmo.ANSWERED
    )

    active_organizations = set([Score.objects.get(
        pk=oco.object_pk).task.organization for oco in org_all_comments])
    for active_organization in active_organizations:
        active_org_comments_count = org_all_comments.filter(
            object_pk__in=scores.filter(
                task__organization=active_organization)).count()
        try:
            task = Task.approved_tasks.get(organization=active_organization)
        except Task.DoesNotExist:
            task = None
        active_organization_stats.append(
            {'org': active_organization,
             'comments_count': active_org_comments_count,
             'task': task})

    active_iifd_person_stats = User.objects.filter(
        comment_comments__pk__in=iifd_all_comments).annotate(
            comments_count=Count('comment_comments'))

    for org_comment in org_comments:
        from exmo2010.utils import workday_count
        delta = timedelta(days=1)
        #check time_to_answer
        if workday_count(org_comment.submit_date.date() + delta,
                         end_date) == time_to_answer:
            fail_soon_comments_without_reply.append(org_comment)
        elif workday_count(org_comment.submit_date.date() + delta,
                           end_date) > time_to_answer:
            fail_comments_without_reply.append(org_comment)
        else:
            comments_without_reply.append(org_comment)

    #комментарии без ответа
    result['comments_without_reply'] = comments_without_reply
    #просроченные комментарии без ответа
    result['fail_comments_without_reply'] = fail_comments_without_reply
    #комментарии с ответом
    result['comments_with_reply'] = comments_with_reply
    #комментарии без ответа; срок ответа истечет в течении суток
    result['fail_soon_comments_without_reply'] = fail_soon_comments_without_reply
    #комментарии с ответом, но ответ был позже срока
    result['fail_comments_with_reply'] = fail_comments_with_reply
    #неотвеченные комментарии представителей
    result['org_comments'] = org_comments
    #все комментарии экспертов
    result['org_all_comments'] = org_all_comments
    #статистика активных (оставивших хоть один комментарий) организаций
    #лист словарей: [{'org': org1, 'comments_count': 1}, ...]
    result['active_organization_stats'] = active_organization_stats
    #статистика ответов по экспертам
    result['active_iifd_person_stats'] = active_iifd_person_stats
    #комментарии экспертов
    result['iifd_all_comments'] = iifd_all_comments
    #всего огранизаций
    result['total_org'] = total_org
    #зарегистрированных организаций
    result['reg_org'] = reg_org
    #дата начала взаимодействия
    result['start_date'] = start_date
    #дата окончания отчетного периода
    result['end_date'] = end_date
    #срок ответа на комментарии (в днях)
    result['time_to_answer'] = time_to_answer

    return result
