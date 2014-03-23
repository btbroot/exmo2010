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
import string
import random
import re

from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from south.modelsinspector import add_introspection_rules

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
            raise ValidationError(ugettext('Illegal symbols in email field.'))
        emails = re.findall(email_re, value)
        addresses = ""
        for e in emails:
            email = e[0] + ", "
            addresses += email
        return addresses.rstrip(", ")

add_introspection_rules([], ["^exmo2010\.models\.organization\.EmailsField"])


def format_phone(phone):
    if not phone:
        return None
    phone = phone.strip()
    if not phone_re.match(phone):
        return None
    if re.search(r'[ \-]', phone):
        return phone
    else:
        ntmp = re.findall(phone_re_reverse, phone[::-1])[0]
        return ntmp[3][::-1] + ntmp[2][::-1] + "-" + ntmp[1][::-1] + "-" + ntmp[0][::-1]


class PhonesField(models.TextField):
    def to_python(self, value):
        sub_phones = re.sub(phone_re, '', value)
        sub_phones = re.sub(delimiters_re, '', sub_phones)
        if sub_phones:
            raise ValidationError(ugettext('Illegal symbols in phone field.'))
        return ', '.join(filter(None, map(format_phone, re.split(r'[,\n\r]+', value))))


add_introspection_rules([], ["^exmo2010\.models\.organization\.PhonesField"])


class Organization(BaseModel):
    """ Fields:
    name -- Unique organization name
    url -- Internet site URL
    email -- list of emails
    phone -- list of phones

    """
    class Meta(BaseModel.Meta):
        ordering = ('name',)
        unique_together = tuple(('name_%s' % lang[0], 'monitoring') for lang in settings.LANGUAGES)

    name = models.CharField(max_length=255, verbose_name=_('name'))
    url = models.URLField(max_length=255, null=True, blank=True, verbose_name=_('Website'))
    email = EmailsField(null=True, blank=True, verbose_name=_('email'))
    phone = PhonesField(null=True, blank=True, verbose_name=_('phone'))

    # Set editable=False attribute on "monitoring".
    # This is workaround for Django bug 13091 https://code.djangoproject.com/ticket/13091
    # See note on OrgEditView.get_form_class() method
    # Used in OrgEditView and organization_list view (which includes Organization creation form)
    monitoring = models.ForeignKey("Monitoring", verbose_name=_('monitoring'), editable=False)

    inv_code = models.CharField(
        verbose_name=_("Invitation code"), blank=True,
        max_length=6, unique=True, editable=False)

    inv_status = models.CharField(
        max_length=3, choices=INV_STATUS, default='NTS',
        verbose_name=_('Invitation status'), editable=False)

    objects = OrganizationMngr()

    def save(self, *args, **kwargs):
        if not self.pk and not self.inv_code:
            self.inv_code = generate_inv_code(6)
        super(Organization, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name


class InviteOrgs(BaseModel):
    """
    Invites organizations history.

    """
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('date and time'), editable=False)
    monitoring = models.ForeignKey("Monitoring", verbose_name=_('monitoring'), editable=False)
    subject = models.TextField(verbose_name=_('subject'))
    comment = models.TextField(verbose_name=_('Letter content'))
    inv_status = models.CharField(max_length=3,
                                  choices=INV_STATUS_ALL, default='ALL',
                                  verbose_name=_('Invitation status'))
