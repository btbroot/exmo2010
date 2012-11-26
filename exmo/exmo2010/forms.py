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
Формы EXMO2010
"""

import string
import time
from django import forms
from django.utils import formats
from django.utils.safestring import mark_safe
from exmo2010.models import Score, Task
from exmo2010.models import Parameter
from exmo2010.models import Claim
from exmo2010.models import Monitoring
from exmo2010.models import MonitoringStatus
from exmo2010.models import Organization
from exmo2010.models import UserProfile
from django.contrib.auth.models import User
from django.utils.translation import ungettext
from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.admin import widgets
from django.core.exceptions import ObjectDoesNotExist
from exmo2010.widgets import TagAutocomplete
from annoying.decorators import autostrip

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

COMMENT_NOTIFICATION_CHOICES = (
    (0, _('do not send')),
    (1, _('one email per one comment')),
    (2, _('one email for all in time interval')),
    )

SCORE_CHANGE_NOTIFICATION_CHOICES = (
    (0, _('do not send')),
    (1, _('one email per one change')),
    (2, _('one email for all in time interval')),
    )

YES_NO_CHOICES = (
    (1, _('Yes')),
    (0, _('No')),
    )

DIGEST_INTERVALS = (
    (1, _("once in 1 hour")),
    (3, _("once in 3 hours")),
    (6, _("once in 6 hours")),
    (12, _("once in 12 hours")),
    (24, _("once in 24 hours")),
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

PASSWORD_ALLOWED_CHARS = string.ascii_letters + string.digits

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



class ScoreForm(forms.ModelForm):
    """
    Форма выставления оценки
    """
    class Meta:
        model = Score
        widgets = {
            'found': forms.RadioSelect(renderer=HorizRadioRenderer),
            'complete': forms.RadioSelect(renderer=HorizRadioRenderer),
            'topical': forms.RadioSelect(renderer=HorizRadioRenderer),
            'accessible': forms.RadioSelect(renderer=HorizRadioRenderer),
            'document': forms.RadioSelect(renderer=HorizRadioRenderer),
            'hypertext': forms.RadioSelect(renderer=HorizRadioRenderer),
            'image': forms.RadioSelect(renderer=HorizRadioRenderer),
            }
        exclude = ('revision',)



class TaskForm(forms.ModelForm):
    """
    Форма редактирования/создания задачи
    """
    def __init__(self, *args, **kwargs):
        """
        Фильтруем пользователей (нужны только эксперты)
        Фильтруем организации (нужны только из текущего мониторинга)
        """
        self._monitoring = kwargs.get('monitoring')
        if self._monitoring:
            kwargs.pop('monitoring')
        super(TaskForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(groups__name__in = UserProfile.expert_groups, is_active = True).distinct()
        if self._monitoring:
            self.fields['organization'].queryset = Organization.objects.filter(monitoring = self._monitoring)

    def clean_user(self):
        """
        Проверка на активность пользователя которому была назначена задача
        """
        user = self.cleaned_data['user']
        user_obj=User.objects.filter(username=user, is_active=True)
        if not user_obj:
            raise forms.ValidationError(_("This user account is inactive"))
        return user

    def clean_organization(self):
        """
        Проверка на соответствие мониторинга
        """
        organization = self.cleaned_data['organization']
        if self._monitoring:
            if Organization.objects.filter(pk=organization.pk, monitoring = self._monitoring).count() < 1:
                raise forms.ValidationError(_("Illegal monitoring"))
        return organization

    class Meta:
        model = Task


class ParamCritScoreFilterForm(forms.Form):
    """Форма фильтрации оценок по параметру и значениям критериев.
    Кроме стандартных вариантов оценок у критерия, добавляем вариант 5,
    означающий, что ничего не выбрано и фильтрация по этому критерию не нужна.
    """
    parameter = forms.ModelChoiceField(label=_('Parameter'),
        queryset=Parameter.objects.none(), empty_label="")
    found = forms.ChoiceField(label=_('Found'), choices=SCORE_CHOICES1,
        initial=5, widget=forms.RadioSelect)
    complete = forms.ChoiceField(label=_('Complete'), choices=SCORE_CHOICES2,
        initial=5, widget=forms.RadioSelect)
    topical = forms.ChoiceField(label=_('Topical'), choices=SCORE_CHOICES2,
        initial=5, widget=forms.RadioSelect)
    accessible = forms.ChoiceField(label=_('Accessible'),
        choices=SCORE_CHOICES2, initial=5, widget=forms.RadioSelect)
    hypertext = forms.ChoiceField(label=_('Hypertext'), choices=SCORE_CHOICES1,
        initial=5, widget=forms.RadioSelect)
    document = forms.ChoiceField(label=_('Document'), choices=SCORE_CHOICES1,
        initial=5, widget=forms.RadioSelect)
    image = forms.ChoiceField(label=_('Image'), choices=SCORE_CHOICES1,
        initial=5, widget=forms.RadioSelect)
    t_opened = forms.BooleanField(label=_('opened'), required=False,
        initial=True)
    t_closed = forms.BooleanField(label=_('closed'), required=False,
        initial=True)
    t_check = forms.BooleanField(label=_('check'), required=False,
        initial=True)
    t_approved = forms.BooleanField(label=_('approved'), required=False,
        initial=True)
    def __init__(self, *args, **kwargs):
        monitoring = kwargs.pop('monitoring', None)
        super(ParamCritScoreFilterForm, self).__init__(*args, **kwargs)
        self.fields['parameter'].queryset = Parameter.objects.filter(
            monitoring=monitoring)


class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim


class ClaimReportForm(forms.Form):
    """
    Форма для отчета по претензиям
    """
    expert = forms.ModelChoiceField(queryset = User.objects.all(), label=_('expert'))
    from_date = forms.DateTimeField(label=_('from date'),
        widget=widgets.AdminSplitDateTime,
        input_formats=DATETIME_INPUT_FORMATS)
    to_date = forms.DateTimeField(label=_('to date'),
        widget=widgets.AdminSplitDateTime,
        input_formats=DATETIME_INPUT_FORMATS)


class MonitoringForm(forms.ModelForm):
    """
    Форма редактирования/создания мониторинга
    """
    status = forms.ChoiceField(choices=Monitoring.MONITORING_STATUS,
        label=_('status'))
    add_questionnaire = forms.BooleanField(required=False,
        label=_('Add questionnaire'))
    class Meta:
        model = Monitoring
        exclude = ('time_to_answer',)

    class Media:
        css = {
            'all': (
                settings.STATIC_URL + 'exmo2010/css/jquery-ui.css',
                settings.STATIC_URL + 'exmo2010/css/exmo2010-base.css',
                )
        }
        js = (
            settings.STATIC_URL + 'exmo2010/js/jquery/jquery.min.js',
            settings.STATIC_URL + 'exmo2010/js/jquery/jquery-ui.min.js',
            )



from django.forms.models import BaseInlineFormSet
class MonitoringStatusBaseFormset(BaseInlineFormSet):
    """
    Формсет для календаря мониторинга
    """
    def get_queryset(self):
        if not hasattr(self, '_queryset'):
            self._queryset = self.queryset.filter(
                status__in=Monitoring.MONITORING_EDIT_STATUSES.keys()
            )
        return self._queryset


class MonitoringStatusForm(forms.ModelForm):
    """
    Базовая форма для формсета календаря мониторинга
    """
    def __init__(self, *args, **kwargs):
        ms = kwargs.get('instance')
        super(MonitoringStatusForm, self).__init__(*args, **kwargs)
        #убираем возможность выбора для поля
        self.fields['status'].choices = ((ms.status, ms),)
        #по умолчанию метка берется из модели
        self.fields['start'].label = Monitoring.MONITORING_EDIT_STATUSES[ms.status]
        #по умолчанию, поле в моделе необязательное,
        #а для формы здесь меняем его свойство, т.к. здесь уже обязательно его указание
        self.fields['start'].required = True

    class Meta:
        model = MonitoringStatus
        widgets = {
            'start': forms.DateInput(attrs={
                'class': 'jdatefield',
                'maxlength': 300
            }),
            'status': forms.HiddenInput(),
            }


class ParameterForm(forms.ModelForm):
    """
    Форма редактирования/создания параметра
    """
    def __init__(self, *args, **kwargs):
        """
        Фильтруем организации для поля exclude
        """
        _parameter = kwargs.get('instance')
        _monitoring = kwargs.get('monitoring')
        if _monitoring:
            kwargs.pop('monitoring')
        super(ParameterForm, self).__init__(*args, **kwargs)
        if _parameter:
            self.fields['exclude'].queryset = Organization.objects.filter(monitoring = _parameter.monitoring)
        if _monitoring:
            self.fields['exclude'].queryset = Organization.objects.filter(monitoring = _monitoring)
            self.fields['monitoring'].initial = _monitoring

    class Meta:
        model = Parameter
        widgets = {
            'keywords': TagAutocomplete,
            'exclude': widgets.FilteredSelectMultiple('',is_stacked=False),
            'monitoring': forms.widgets.HiddenInput,
            }

    class Media:
        css = {
            "all": ("exmo2010/selector.css",)
        }


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        exclude = ("inv_code",)
        widgets = {
            'keywords': TagAutocomplete,
            'monitoring': forms.HiddenInput,
            }


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
        if not MonitoringStatus.objects.get(
            monitoring = self.monitoring,
            status = Monitoring.MONITORING_INTERACT).start:
            raise forms.ValidationError(_('Monitoring interact start '
                                          'date is missing. '
                                          'Check your monitoring calendar'))
        return cleaned_data


class QuestionnaireDynForm(forms.Form):
    """Динамическая форма анкеты с вопросами на странице задачи мониторинга."""
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions')
        self.task = kwargs.pop('task', None)
        super(QuestionnaireDynForm, self).__init__(*args, **kwargs)
        for q in questions:
            if q.qtype == 0:
                self.fields['q_%s' % q.pk] = forms.CharField(label=q.question,
                    help_text=q.comment, max_length=300, required=False,
                    widget=forms.TextInput(attrs={'class': 'aqtext',
                                                  'placeholder': _('Text')}))
            elif q.qtype == 1:
                self.fields['q_%s' % q.pk] = forms.IntegerField(
                    label=q.question, help_text=q.comment, required=False,
                    widget=forms.TextInput(attrs={'class': 'aqint',
                                                  'placeholder': _('Number')}),
                    min_value=0, max_value=4294967295)
            elif q.qtype == 2:
                self.fields['q_%s' % q.pk] = forms.ModelChoiceField(
                    label=q.question, help_text=q.comment, empty_label=None,
                    required=False,
                    queryset=q.answervariant_set.order_by('-pk'),
                    widget=forms.RadioSelect(attrs={'class': 'aqchoice',}))

    def clean(self):
        cleaned_data = self.cleaned_data
        for answ in cleaned_data.items():
            if answ[0].startswith("q_") and not answ[1]\
               and self.task and self.task.approved:
                raise forms.ValidationError(_('Cannot delete answer for '
                                      'approved task. Edit answer instead.'))
        return cleaned_data


class EmailReadonlyWidget(forms.Widget):
    def render(self, name, value=" ", attrs=None):
        html = '<p id="id_%(name)s" name="%(name)s">%(value)s</p>' % \
               {'name': name, 'value': value}
        return mark_safe(html)


@autostrip
class SettingsPersInfForm(forms.Form):
    """
    Форма для блока "Личная информация" страницы настроек пользователя.
    Версия для пользователя, не являющегося представителем организации.
    """
    # required=False у email потому, что не предполагается сабмит этого поля
    # из-за кастомного виджета.
    first_name = forms.CharField(label=_("First name"),
        widget=forms.TextInput(attrs={"maxlength": 14}),
        required=False, max_length=14)
    patronymic = forms.CharField(label=_("Patronymic"),
        widget=forms.TextInput(attrs={"maxlength": 14}),
        required=False, max_length=14)
    last_name = forms.CharField(label=_("Last name"),
        widget=forms.TextInput(attrs={"maxlength": 30}),
        required=False, max_length=30)


@autostrip
class SettingsPersInfFormFull(SettingsPersInfForm):
    """
    Форма для блока "Личная информация" страницы настроек пользователя.
    Версия для пользователя, являющегося представителем организации.
    """
    position = forms.CharField(label=_("Seat"),
        widget=forms.TextInput(attrs={"maxlength": 48}),
        required=False, max_length=48)
    phone = forms.CharField(label=_("Phone"),
        widget=forms.TextInput(attrs={"maxlength": 30}),
        required=False, max_length=30)


@autostrip
class SettingsInvCodeForm(forms.Form):
    """
    Форма для блока "Код приглашения" страницы настроек пользователя.
    """
    invitation_code = forms.CharField(label=_("New code"),
        widget=forms.TextInput(attrs={"maxlength": 6}),
        max_length=6, min_length=6)

    def clean_invitation_code(self):
        invitation_code = self.cleaned_data.get("invitation_code")
        try:
            organization = Organization.objects.get(inv_code=invitation_code)
        except ObjectDoesNotExist:
            time.sleep(3)  # Чтобы усложнить перебор.
            raise forms.ValidationError("")  # Текст ошибки не нужен.
        else:
            return invitation_code


class SettingsChPassForm(forms.Form):
    """
    Форма для блока "Сменить пароль" страницы настроек пользователя.
    """
    old_password = forms.CharField(label=_("Old password"),
        widget=forms.PasswordInput(attrs={"maxlength": 24},
            render_value=True), required=False)
    new_password = forms.CharField(label=_("New password"),
        widget=forms.TextInput(attrs={"maxlength": 24, "autocomplete": "off"}),
            required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(SettingsChPassForm, self).__init__(*args, **kwargs)

    def clean_old_password(self):
        if not self.user.check_password(self.cleaned_data.get("old_password")):
            raise forms.ValidationError(_("Failed to change password: "
                                          "submitted wrong current password"))

    def clean_new_password(self):
        """Проверка пароля на наличие недопустимых символов."""
        new_password = self.cleaned_data.get('new_password')
        if not new_password:
            # Ставим заведомо недопустимый символ.
            new_password = "@"
        for char in new_password:  # Проверять на наличие пароля необязательно.
            if char not in PASSWORD_ALLOWED_CHARS:
                raise forms.ValidationError(_("Failed to change password: "
                                              "it can contain only latin "
                                              "characters (A-Z, a-z) and "
                                              "digits (0-9)"))
        return new_password


class SettingsSendNotifForm(forms.Form):
    """
    Форма для блока "Рассылка уведомлений" страницы настроек пользователя.
    Версия для пользователя, не являющегося представителем организации.
    """
    # Скрытое поле, нужное для того, чтобы однозначно идентифицировать форму,
    # т.к. при снятой галке у subscribe, django вообще не кладет
    # это поле (subscribe) в POST.
    snf = forms.IntegerField(widget=forms.HiddenInput, required=False)
    subscribe = forms.BooleanField(label="",
        help_text=_("Subscribe to news e-mail notification"), required=False)


class SettingsSendNotifFormFull(SettingsSendNotifForm):
    """
    Форма для блока "Рассылка уведомлений" страницы настроек пользователя.
    Версия для пользователя, являющегося представителем организации.
    """
    comment_notification_type = forms.ChoiceField(
        choices=COMMENT_NOTIFICATION_CHOICES,
        label=_('Comment notification'))
    comment_notification_digest = forms.ChoiceField(choices=DIGEST_INTERVALS,
        required=False)
    score_notification_type = forms.ChoiceField(
        choices=SCORE_CHANGE_NOTIFICATION_CHOICES,
        label=_('Score change notification'))
    score_notification_digest = forms.ChoiceField(choices=DIGEST_INTERVALS,
        required=False)
    notify_on_my_comments = forms.BooleanField(label="",
        help_text=_("Send to me my comments"), required = False)

    def __init__(self, *args, **kwargs):
        super(SettingsSendNotifFormFull, self).__init__(*args, **kwargs)


class ParameterTypeForm(forms.ModelForm):
    """Форма для использования в формсете
     на странице установки типа параметра.
     """
    class Meta:
        model = Parameter
        fields = ('npa',)
    def __init__(self, *args, **kwargs):
        super(ParameterTypeForm, self).__init__(*args, **kwargs)
        self.fields['npa'].label = self.instance.name


class ParameterDynForm(forms.Form):
    """Динамическая форма параметров мониторинга."""
    def __init__(self, *args, **kwargs):
        monitoring = kwargs.pop('monitoring')
        super(ParameterDynForm, self).__init__(*args, **kwargs)
        for p in Parameter.objects.filter(monitoring=monitoring):
            self.fields['parameter_%s' % p.pk] = forms.BooleanField(label=p.name,
                help_text=p.description, required=False,
            )

class MonitoringFilterForm(forms.Form):
    """
    Форма выбора мониторинга. К выбору доступны лишь опубликованные
    """
    monitoring = forms.ModelChoiceField(
        queryset = Monitoring.objects.filter(status=Monitoring.MONITORING_PUBLISH).extra(select={
                'start_date': Monitoring().prepare_date_sql_inline(Monitoring.MONITORING_PUBLISH),
            }).order_by('-start_date'),
        required=False,
        empty_label=_('monitoring not select'),
        )
