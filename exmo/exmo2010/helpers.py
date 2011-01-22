# This file is part of EXMO2010 software.
# Copyright 2010 Al Nikolov
# Copyright 2010 Institute for Information Freedom Development
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
#from contrib.admin
from django.utils.translation import ugettext_lazy, ugettext as _
from django.utils.text import capfirst, get_text_list
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse



def construct_change_message(request, form, formsets):
        """
        Construct a change message from a changed object.
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


priv_list = [
    'TASK_ADMIN',
    'TASK_EXPERT',
    'TASK_VIEW',
    'SCORE_COMMENT',
    ]

def check_permission(user, priv, context = None):
    '''check user permission for context'''
    if priv not in priv_list: return False
    if user.is_superuser and user.is_active: return True
    if context == None:
        return False

    groups = user.groups.all()
    if context._meta.object_name == 'Task':
        task = context
        if Group.objects.get(name='experts') in groups and user == task.user and task.open and priv == 'TASK_EXPERT':
            return True
        if Group.objects.get(name='experts') in groups and user == task.user and priv == 'TASK_VIEW':
            return True
        elif Group.objects.get(name='customers') in groups and task.approved and priv == 'TASK_VIEW':
            return True
        elif Group.objects.get(name='organizations') in groups and task.approved and priv == 'TASK_VIEW':
            try:
                g = Group.objects.get(name = task.organization.keyname)
                if g in groups:
                    return True
                else:
                    return False
            except:
                return False

    if context._meta.object_name == 'Score':
        task = context.task
        if Group.objects.get(name='organizations') in groups and task.approved and priv == 'SCORE_COMMENT':
            try:
                g = Group.objects.get(name = task.organization.keyname)
                if g in groups:
                    return True
                else:
                    return False
            except:
                return False

    return False

def get_recipients_admin(comment):
    score = comment.content_object
    res = []
    for user in User.objects.filter(is_superuser = True):
        if user.email and user.is_active:
            res.append(user.email)
    if score.task.user.email and score.task.user.is_active:
        res.append(score.task.user.email)
    if comment.user.is_superuser or comment.user == score.task.user:
        if comment.user.email and comment.user.is_active: res.append(comment.user.email)
        if comment.user_email and comment.user.is_active: res.append(comment.user_email)
    return list(set(res))

def get_recipients_nonadmin(comment):
    score = comment.content_object
    res = []
    try:
        if score.task.approved:
            g = Group.objects.get(name = score.task.organization.keyname)
            users = User.objects.filter(groups = g)
            for u in users:
                if u.email and u.is_active:
                    res.append(u.email)
    except:
        pass
    if not comment.user.is_superuser and not comment.user == score.task.user:
        if comment.user.email and comment.user.is_active: res.append(comment.user.email)
        if comment.user_email and comment.user.is_active: res.append(comment.user_email)
    for r in get_recipients_admin(comment):
        try:
            res.remove(r)
        except:
            pass
    return list(set(res))



from django.core.mail import send_mail
from django.template import loader, Context
from django.conf import settings
def comment_notification(sender, **kwargs):
    comment = kwargs['comment']
    request = kwargs['request']
    score = comment.content_object
    subject = u'%(prefix)s%(monitoring)s - %(org)s: %(code)s' % {
            'prefix': settings.EMAIL_SUBJECT_PREFIX,
            'monitoring': score.task.monitoring,
            'org': score.task.organization.name.split(':')[0],
            'code': score.parameter.fullcode(),
            }
    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http', request.get_host(), reverse('exmo.exmo2010.views.score_detail_direct', args=[score.pk, 'view']))
    t = loader.get_template('exmo2010/score_comment_email.html')
    c = Context({ 'score': score, 'user': comment.user, 'admin': False, 'comment':comment, 'url': url })
    message = t.render(c)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, get_recipients_nonadmin(comment))

    t = loader.get_template('exmo2010/score_comment_email.html')
    c = Context({ 'score': comment.content_object, 'user': comment.user, 'admin': True, 'comment':comment, 'url': url })
    message = t.render(c)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, get_recipients_admin(comment))


def claim_notification(sender, **kwargs):
    claim = kwargs['claim']
    request = kwargs['request']
    score = claim.score
    subject = _('%(prefix)s%(monitoring)s - %(org)s: %(code)s - New claim') % {
            'prefix': settings.EMAIL_SUBJECT_PREFIX,
            'monitoring': score.task.monitoring,
            'org': score.task.organization.name.split(':')[0],
            'code': score.parameter.fullcode(),
            }
    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http', request.get_host(), reverse('exmo.exmo2010.views.score_detail_direct', args=[score.pk, 'update']))
    t = loader.get_template('exmo2010/claim_email.html')
    c = Context({ 'score': claim.score, 'claim': claim, 'url': url })
    message = t.render(c)
    if score.task.user.email:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [score.task.user.email])
