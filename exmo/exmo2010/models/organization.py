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

import string
import random
import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext as _
from south.modelsinspector import add_introspection_rules
from tagging.models import Tag

from core.fields import TagField
from .base import BaseModel


INV_CODE_CHARS = string.ascii_uppercase + string.digits

INV_STATUS = [
    ('NTS', _('Not sent')),
    ('SNT', _('Sent')),
    ('RD', _('Read')),
    ('RGS', _('Registered')),
    ('ACT', _('Activated')),
]

INV_STATUS_ALL = [('ALL', _('All invitations'))] + INV_STATUS


def generate_inv_code(ch_nr):
    """Генерит код приглашения с указанным количеством символов."""
    return "".join(random.sample(INV_CODE_CHARS, ch_nr))


class OrganizationMngr(models.Manager):
    """
    Менеджер с одним специальным методом для генерации кодов приглашения
     для всех орг-ий, у которых его нет.
    """
    def create_inv_codes(self):
        orgs = self.filter(inv_code="")
        for o in orgs:
            o.inv_code = generate_inv_code(6)
            o.save()


phone_re = re.compile(r'([+])?([\d()\s\-]+)[-\.\s]?(\d{2})[-\.\s]?(\d{2})')
phone_re_reverse = re.compile(r'(\d{2})[-\.\s]?(\d{2})[-\.\s]?([\d()\s\-]+)([+])?')
email_re = re.compile(r'([0-9a-zA-Z]([-\.\w]*[0-9a-zA-Z])*@([0-9a-zA-Z][-\w]*[0-9a-zA-Z]\.)+[a-zA-Z]{2,9})')
delimiters_re = re.compile(r',|\s||(,\s)|\n|(,\n)')


class EmailsField(models.TextField):
    def to_python(self, value):
        sub_emails = re.sub(email_re, '', value)
        sub_emails = re.sub(delimiters_re, '', sub_emails)
        if sub_emails:
            raise ValidationError(_('Illegal symbols in email field.'))
        emails = re.findall(email_re, value)
        addresses = ""
        for e in emails:
            email = e[0] + ", "
            addresses += email
        return addresses.rstrip(", ")

add_introspection_rules([], ["^exmo2010\.models\.EmailsField"])


class PhonesField(models.TextField):
    def to_python(self, value):
        sub_phones = re.sub(phone_re, '', value)
        sub_phones = re.sub(delimiters_re, '', sub_phones)
        if sub_phones:
            raise ValidationError(_('Illegal symbols in phone field.'))
        phones = re.split(r',|\n', value)
        numbers = ""
        for p in phones:
            p = p.rstrip()
            p = p.lstrip()
            if " " in p or "-" in p:
                number = p
            else:
                ntmp = re.findall(phone_re_reverse, p[::-1])[0]
                number = ntmp[3][::-1] + ntmp[2][::-1] + "-" + ntmp[1][::-1] + "-" + ntmp[0][::-1]

            number += ", "
            numbers += number
        return numbers.rstrip(", ")

add_introspection_rules([], ["^exmo2010\.models\.PhonesField"])


class Organization(BaseModel):
    """ Fields:
    name -- Unique organization name
    url -- Internet site URL
    email -- list of emails
    phone -- list of phones
    keywords -- Keywords for autocomplete and search (not used)
    comments -- Additional comment (not used)

    """
    class Meta(BaseModel.Meta):
        ordering = ('name',)
        unique_together = (('name', 'monitoring'),)

    name = models.CharField(max_length=255, verbose_name=_('name'))
    url = models.URLField(max_length=255, null=True, blank=True, verify_exists=False, verbose_name=_('url'))
    keywords = TagField(null=True, blank=True, verbose_name=_('keywords'))
    email = EmailsField(null=True, blank=True, verbose_name=_('email'))
    phone = PhonesField(null=True, blank=True, verbose_name=_('phone'))
    comments = models.TextField(null=True, blank=True, verbose_name=_('comments'))
    monitoring = models.ForeignKey("Monitoring", verbose_name=_('monitoring'))
    inv_code = models.CharField(verbose_name=_("Invitation code"), blank=True, max_length=6, unique=True)
    inv_status = models.CharField(max_length=3,
                                  choices=INV_STATUS, default='NTS',
                                  verbose_name=_('Invitation status'))

    objects = OrganizationMngr()

    def save(self, *args, **kwargs):
        if not self.pk and not self.inv_code:
            self.inv_code = generate_inv_code(6)
        super(Organization, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

    def _get_tags(self):
        return Tag.objects.get_for_object(self)

    def _set_tags(self, tag_list):
        Tag.objects.update_tags(self, tag_list)

    tags = property(_get_tags, _set_tags)


class InviteOrgs(BaseModel):
    """
    Invites organizations history.

    """
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('date and time'))
    monitoring = models.ForeignKey("Monitoring", verbose_name=_('monitoring'))
    comment = models.TextField(verbose_name=_('comment'))
    inv_status = models.CharField(max_length=3,
                                  choices=INV_STATUS_ALL, default='ALL',
                                  verbose_name=_('Invitation status'))


class EmailTasks(BaseModel):
    """
    Model with tasks ids for each organization (used by celery).

    """
    organization = models.ForeignKey(Organization, verbose_name=_('organization'))
    task_id = models.CharField(max_length=60, verbose_name=_('task id'), db_index=True)

