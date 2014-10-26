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
import string
import random
import re

from ckeditor.fields import RichTextField
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.utils.translation import pgettext, pgettext_lazy, ugettext, ugettext_lazy as _
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


phone_re = re.compile(r'([+()\d\s\-]{3,25})')
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

    # 1234567 -> 123-45-67
    if re.search(r'\d{5}$', phone):
        return '-'.join([phone[:-4], phone[-4:-2], phone[-2:]])

    # 123 4567 -> 123 45-67
    if re.search(r'\d{4}$', phone):
        return '-'.join([phone[:-2], phone[-2:]])

    return phone


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
        verbose_name = pgettext_lazy(u'change organization in admin', u'Organization')
        verbose_name_plural = _('Organizations')

    name = models.CharField(max_length=255, verbose_name=_('name'))
    url = models.URLField(max_length=255, null=True, blank=True, verbose_name=_('Website'))
    email = EmailsField(null=True, blank=True, verbose_name=_('email'))
    phone = PhonesField(null=True, blank=True, verbose_name=_('phone'))
    monitoring = models.ForeignKey("Monitoring", verbose_name=_('monitoring'), editable=False)

    inv_code = models.CharField(
        verbose_name=_("Invitation code"), blank=True,
        max_length=6, unique=True, editable=False)

    inv_status = models.CharField(
        max_length=3, choices=INV_STATUS, default='NTS',
        verbose_name=_('Invitation status'), editable=False)

    objects = OrganizationMngr()

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk and not self.inv_code:
            self.inv_code = generate_inv_code(6)
        super(Organization, self).save(*args, **kwargs)

    def validate_unique(self, exclude=None):
        """
        Prevent "monitoring" field from being excluded in validation checks.
        This is workaround for Django bug 13091 https://code.djangoproject.com/ticket/13091

        This workaround will force modelform to validate unique_together constraints involving
        "monitoring" field on the model, even if "monitoring" field is absent in the form.
        - Failing to do that will raise IntegrityError on instance saving.

        """
        if 'monitoring' in exclude:
            exclude.remove('monitoring')
        super(Organization, self).validate_unique(exclude)

    def clean(self):
        """
        Replace empty strings with None for all modeltranslation fields to store NULL in database.
        This will allow multiple orgs with empty modeltranslation fields to pass unique checks during form validation.
        """
        from exmo2010.translation import OrganizationTranslationOptions
        for field in OrganizationTranslationOptions.fields:
            for lang in settings.LANGUAGES:
                if not getattr(self, '{}_{}'.format(field, lang[0])):
                    setattr(self, '{}_{}'.format(field, lang[0]), None)

    def email_iter(self):
        if not self.email:
            return

        for email in self.email.replace(' ', '').split(','):
            if email:
                yield email


class InviteOrgs(BaseModel):
    """
    Invites organizations history.

    """
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('date and time'), editable=False)
    monitoring = models.ForeignKey("Monitoring", verbose_name=_('monitoring'), editable=False)
    subject = models.TextField(verbose_name=_('subject'))
    comment = RichTextField(config_name='simplified', verbose_name=_('Letter content'))
    inv_status = models.CharField(max_length=3,
                                  choices=INV_STATUS_ALL, default='ALL',
                                  verbose_name=_('Invitation status'))
    dst_orgs_noreg = models.BooleanField(default=False, verbose_name=pgettext_lazy(u'(organizations)', u'Not registered'))
    dst_orgs_inact = models.BooleanField(default=False, verbose_name=pgettext_lazy(u'(organizations)', u'Inactive'))
    dst_orgs_activ = models.BooleanField(default=False, verbose_name=pgettext_lazy(u'(organizations)', u'Active'))

    def dst_orgs_display(self):
        if self.dst_orgs_noreg and self.dst_orgs_inact and self.dst_orgs_activ:
            return pgettext(u'(organizations)', u'All')
        else:
            verbose_names = []
            for attr in ['dst_orgs_noreg', 'dst_orgs_inact', 'dst_orgs_activ']:
                if getattr(self, attr):
                    verbose_names.append(unicode(self._meta.get_field(attr).verbose_name))
            return ', '.join(verbose_names)

    dst_orgusers_inact = models.BooleanField(default=False, verbose_name=pgettext_lazy(u'(representatives)', u'Inactive'))
    dst_orgusers_activ = models.BooleanField(default=False, verbose_name=pgettext_lazy(u'(representatives)', u'Active'))

    def dst_orgusers_display(self):
        if self.dst_orgusers_inact and self.dst_orgusers_activ:
            return pgettext(u'(representatives)', u'All')
        else:
            verbose_names = []
            for attr in ['dst_orgusers_inact', 'dst_orgusers_activ']:
                if getattr(self, attr):
                    verbose_names.append(unicode(self._meta.get_field(attr).verbose_name))
            return ', '.join(verbose_names)

    def clean(self):
        dst = 'dst_orgs_noreg dst_orgs_inact dst_orgs_activ dst_orgusers_inact dst_orgusers_activ'.split()
        if not any(getattr(self, attr) for attr in dst):
            raise ValidationError(_(u'Message should have destination organizations or representatives'))
