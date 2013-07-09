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
import json
import os
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.utils.translation import ugettext as _
from livesettings import config_value
from reversion.models import Version

from core.tasks import send_email
from digest_email.models import DigestJournal
from exmo2010.models import Score


class DigestSend(object):
    """
    Digest common class.

    """
    __metaclass__ = ABCMeta

    digest = None
    users = None
    request = HttpRequest()

    def __init__(self, digest):
        # get digest name:
        self.digest = digest
        # get all users for digest:
        users = User.objects.filter(digestpreference__digest=self.digest, email__isnull=False).exclude(email__exact='')
        # in PostgreSQL = .distinct('email'), but for MySQL it look like this:
        self.users = User.objects.filter(email__in=users.values_list('email', flat=True)
                                                        .order_by('email')
                                                        .distinct())

    @abstractmethod
    def get_content(self, user, scores, last_date):
        """
        Abstract method to getting content for emails.

        """
        return

    def send(self, extra_context=None):
        """
        Send digest emails.

        """
        now = datetime.now()
        current_site = Site.objects.get_current()
        template = self.digest.name.replace(' ', '_')
        protocol = self.request.is_secure() and 'https' or 'http'
        expert = _(config_value('GlobalParameters', 'EXPERT'))

        subject = _("%(prefix)sEmail digest for %(digest)s") % {
            'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
            'digest': self.digest,
        }

        for user in self.users:
            digest_pref = user.digestpreference_set.get(digest=self.digest)
            last_digest_date = self.digest.get_last(user)
            last_date = now - timedelta(hours=digest_pref.interval)
            if last_date < last_digest_date:
                continue

            scores = Score.objects
            if user.userprofile.is_expertA:
                scores = scores.all()
            elif user.userprofile.is_expertB:
                scores = scores.filter(task__user=user)
            elif user.userprofile.is_organization:
                scores = scores.filter(task__organization__in=user.userprofile.organization.all())
            else:
                continue

            object_list = self.get_content(user, scores, last_date)
            if object_list:
                c = {
                    'user': user,
                    'from': last_date,
                    'till': now,
                    'site': current_site,
                    'object_list': object_list,
                    'digest': self.digest,
                    'protocol': protocol,
                    'expert': expert,
                }

                if extra_context:
                    c.update(extra_context)

                send_email(user.email, subject, template, context=c)

                journal = DigestJournal(user=user, digest=self.digest)
                journal.save()


class CommentDigest(DigestSend):
    """
    Inheritance class for comment digest only.

    """
    def get_content(self, user, scores, last_date):
        """
        Get comments for digest.

        """
        qs = Comment.objects.filter(
            content_type__model='score',
            submit_date__gte=last_date,
            object_pk__in=scores,
        ).order_by('submit_date')

        if not user.userprofile.notify_comment_preference['self']:
            qs = qs.exclude(user=user)
        return qs


class ScoreDigest(DigestSend):
    """
    Inheritance class for score digest only.

    """
    def get_content(self, user, scores, last_date):
        """
        Get scores for digest.

        """
        result = []
        current_site = Site.objects.get_current()
        scores = scores.filter(edited__gte=last_date)

        for score in scores:
            qs = Version.objects.filter(object_id_int=score.pk) \
                        .values_list('serialized_data', flat=True) \
                        .order_by('-id')

            url = '%s://%s%s' % (self.request.is_secure() and 'https' or 'http',
                                 current_site, reverse('exmo2010:score_view', args=[score.pk]))
            result_item = {
                'organization': score.task.organization,
                'parameter': score.parameter,
                'url': url,
                'fields': {}
            }

            last_revision = json.loads(qs[0])[0]['fields']

            if len(qs) > 1:
                penultimate_revision = json.loads(qs[1])[0]['fields']

            for field, value in last_revision.items():
                if value:
                    item = penultimate_revision[field] if len(qs) > 1 else None
                    if field not in ['created', 'edited', 'parameter', 'revision', 'task'] and value != item:
                        result_item['fields'].update({field: {'was': item, 'now': value}})
            result.append(result_item)

        return result
