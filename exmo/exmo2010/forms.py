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

"""
Формы EXMO2010
"""

from django import forms
from django.utils import formats
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.utils.translation import ungettext
from django.utils.translation import ugettext as _
from django.conf import settings

from exmo2010.models import Claim, Parameter


DATETIME_INPUT_FORMATS = formats.get_format('DATETIME_INPUT_FORMATS') + ('%d.%m.%Y %H:%M:%S',)

# основные JS ресурсы для форм с виджетами из админки
CORE_JS = (
    settings.ADMIN_MEDIA_PREFIX + 'js/core.js',
    settings.ADMIN_MEDIA_PREFIX + 'js/admin/RelatedObjectLookups.js',
    settings.STATIC_URL + 'exmo2010/js/jquery/jquery.min.js',
    settings.ADMIN_MEDIA_PREFIX + 'js/jquery.init.js',
    settings.ADMIN_MEDIA_PREFIX + 'js/actions.min.js',
)

CORE_MEDIA = forms.Media(js=CORE_JS)

YES_NO_CHOICES = (
    (1, _('Yes')),
    (0, _('No')),
)

SCORE_CHOICES1 = (
    (5, "-"),
    (0, "0"),
    (1, "1"),
)

SCORE_CHOICES2 = (
    (5, "-"),
    (1, "1"),
    (2, "2"),
    (3, "3"),
)

ANSWER_TIME_CHOICES = [(d, ungettext('%(count)d day',
    '%(count)d days', d) % {"count": d}) for d in range(1, 11)]


from django.utils.html import escape
def add_required_label_tag(original_function):
    """Adds the 'required' CSS class and an asterisks to required field labels."""
    def required_label_tag(self, contents=None, attrs=None):
        contents = contents or escape(self.label)
        if self.field.required:
            if not self.label.endswith("*"):
                self.label += "*"
                contents += "*"
            attrs = {'class': 'required'}
        return original_function(self, contents, attrs)
    return required_label_tag


def decorate_bound_field():
    from django.forms.forms import BoundField
    BoundField.label_tag = add_required_label_tag(BoundField.label_tag)
decorate_bound_field()


class HorizRadioRenderer(forms.RadioSelect.renderer):
    """ this overrides widget method to put radio buttons horizontally
        instead of vertically.
    """
    def render(self):
        """Outputs radios"""
        return mark_safe(u'\n'.join([u'%s\n' % w for w in self]))


class ClaimAddForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea,
                              label=_('Your claim'))
    claim_id = forms.IntegerField(required=False,
        widget=forms.widgets.HiddenInput())


class ClarificationAddForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea,
                              label=_('Your clarification'))
    clarification_id = forms.IntegerField(required=False,
        widget=forms.widgets.HiddenInput())


class ClaimForm(forms.Form):
    class Meta:
        model = Claim


class ClaimReportForm(forms.Form):
    """
    Форма для отчета по претензиям.
    """
    creator = forms.ChoiceField()
    addressee = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        creator_id_list = kwargs.pop("creator_id_list")
        addressee_id_list = kwargs.pop("addressee_id_list")
        super(ClaimReportForm, self).__init__(*args, **kwargs)
        creator_choices = [(0, _("all managers"))]
        for i in creator_id_list:
            user = User.objects.get(pk=i)
            name = user.profile.legal_name
            creator_choices.append((i, name))
        self.fields['creator'].choices = creator_choices
        addressee_choices = [(0, _("all experts"))]
        for i in addressee_id_list:
            user = User.objects.get(pk=i)
            name = user.profile.legal_name
            addressee_choices.append((i, name))
        self.fields['addressee'].choices = addressee_choices


class ClarificationReportForm(forms.Form):
    """
    Форма для отчета по претензиям.
    """
    creator = forms.ChoiceField()
    addressee = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        creator_id_list = kwargs.pop("creator_id_list")
        addressee_id_list = kwargs.pop("addressee_id_list")
        super(ClarificationReportForm, self).__init__(*args, **kwargs)
        creator_choices = [(0, _("all managers"))]
        for i in creator_id_list:
            user = User.objects.get(pk=i)
            name = user.profile.legal_name
            creator_choices.append((i, name))
        self.fields['creator'].choices = creator_choices
        addressee_choices = [(0, _("all experts"))]
        for i in addressee_id_list:
            user = User.objects.get(pk=i)
            name = user.profile.legal_name
            addressee_choices.append((i, name))
        self.fields['addressee'].choices = addressee_choices


class MonitoringCommentStatForm(forms.Form):
    """
    Форма отчета по комментариям
    """
    time_to_answer = forms.ChoiceField(
        choices=ANSWER_TIME_CHOICES,
        label = _('Maximum time to answer'))

    def __init__(self, *args, **kwargs):
        self.monitoring = kwargs.pop('monitoring', None)
        super(MonitoringCommentStatForm, self).__init__(*args, **kwargs)

    def clean(self):
        """
        Проверяем что поле начала периода взаимодействия в календаре заполнено
        """
        cleaned_data = self.cleaned_data
        if not self.monitoring.interact_date:
            raise forms.ValidationError(_('Monitoring interact start '
                                          'date is missing. '
                                          'Check your monitoring calendar'))
        return cleaned_data


class EmailReadonlyWidget(forms.Widget):
    def render(self, name, value=" ", attrs=None):
        html = '<p id="id_%(name)s" name="%(name)s">%(value)s</p>' % \
               {'name': name, 'value': value}
        return mark_safe(html)


class ParameterDynForm(forms.Form):
    """Динамическая форма параметров мониторинга."""
    def __init__(self, *args, **kwargs):
        monitoring = kwargs.pop('monitoring')
        super(ParameterDynForm, self).__init__(*args, **kwargs)
        for p in Parameter.objects.filter(monitoring=monitoring):
            self.fields['parameter_%s' % p.pk] = forms.BooleanField(label=p.name,
                help_text=p.description, required=False,
    )
