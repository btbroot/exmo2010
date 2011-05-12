# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 Institute for Information Freedom Development
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
from exmo.helpers import disable_for_loaddata



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
            from exmo.exmo2010 import models
            for profile in models.UserProfile.objects.filter(organization = score.task.organization):
                if profile.user.email and profile.user.is_active:
                    res.append(profile.user.email)
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
    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http', request.get_host(), reverse('exmo.exmo2010.view.score.score_view', args=[score.pk]))
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
    url = '%s://%s%s' % (request.is_secure() and 'https' or 'http', request.get_host(), reverse('exmo.exmo2010.view.score.score_view', args=[score.pk]))
    t = loader.get_template('exmo2010/claim_email.html')
    c = Context({ 'score': claim.score, 'claim': claim, 'url': url })
    message = t.render(c)
    if score.task.user.email:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [score.task.user.email])



from reversion import revision
@disable_for_loaddata
def post_save_model(sender, instance, created, **kwargs):
    must_register = False
    if revision.is_registered(instance.__class__):
        revision.unregister(instance.__class__)
        must_register = True
    #update task openness hook
    from exmo.exmo2010 import models
    if instance.__class__ == models.Score:
        instance.task.update_openness()
    if instance.__class__ == models.Monitoring:
        for task in models.Task.objects.filter(organization__monitoring = instance).all(): task.update_openness()
    if instance.__class__ == models.Task():
        instance.update_openness()
    if must_register:
        revision.register(instance.__class__)



def create_profile(sender, instance, created, **kwargs):
    if created:
        from exmo.exmo2010 import models
        profile = models.UserProfile(user = instance)
        profile.save()



def score_change_notify(sender, **kwargs):
    form = kwargs['form']
    score = form.instance
    request = kwargs['request']
    changes = []
    if form.changed_data:
        for change in form.changed_data:
            change_dict = {'field': change, 'was': form.initial.get(change, form.fields[change].initial), 'now': form.cleaned_data[change]}
            changes.append(change_dict)
    if score.task.approved:
        from exmo.exmo2010 import models
        rcpt = []
        for profile in models.UserProfile.objects.filter(organization = score.task.organization):
            if profile.user.is_active and profile.user.email and profile.notify_score_change:
                rcpt.append(profile.user.email)
        rcpt = list(set(rcpt))
        subject = _('%(prefix)s%(monitoring)s - %(org)s: %(code)s - Score changed') % {
            'prefix': settings.EMAIL_SUBJECT_PREFIX,
            'monitoring': score.task.monitoring,
            'org': score.task.organization.name.split(':')[0],
            'code': score.parameter.fullcode(),
        }
        url = '%s://%s%s' % (request.is_secure() and 'https' or 'http', request.get_host(), reverse('exmo.exmo2010.view.score.score_view', args=[score.pk]))
        t = loader.get_template('exmo2010/score_email.html')
        c = Context({ 'score': score, 'url': url, 'changes': changes, })
        message = t.render(c)
        if rcpt:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, rcpt)
