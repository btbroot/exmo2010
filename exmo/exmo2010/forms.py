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
import string
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
from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.admin import widgets
from exmo2010.widgets import TagAutocomplete
from annoying.decorators import autostrip

DATETIME_INPUT_FORMATS = formats.get_format('DATETIME_INPUT_FORMATS') + ('%d.%m.%Y %H:%M:%S',)

CORE_JS = (
    settings.ADMIN_MEDIA_PREFIX + 'js/core.js',
    settings.ADMIN_MEDIA_PREFIX + 'js/admin/RelatedObjectLookups.js',
    settings.STATIC_URL + 'exmo2010/js/jquery/jquery.min.js',
    settings.ADMIN_MEDIA_PREFIX + 'js/jquery.init.js',
    settings.ADMIN_MEDIA_PREFIX + 'js/actions.min.js',
    )

CORE_MEDIA = forms.Media(js=CORE_JS)

SEX_CHOICES = (
    (1, _("male")),
    (2, _("female")),
    )

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

PASSWORD_ALLOWED_CHARS = string.ascii_letters + string.digits

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
    def __init__(self, *args, **kwargs):
        self._monitoring = kwargs.get('monitoring')
        if self._monitoring:
            kwargs.pop('monitoring')
        super(TaskForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(groups__name__in = UserProfile.expert_groups, is_active = True).distinct()
        if self._monitoring:
            self.fields['organization'].queryset = Organization.objects.filter(monitoring = self._monitoring)

    def clean_user(self):
        user = self.cleaned_data['user']
        user_obj=User.objects.filter(username=user, is_active=True)
        if not user_obj:
            raise forms.ValidationError(_("This user account is inactive"));
        return user

    def clean_organization(self):
        organization = self.cleaned_data['organization']
        if self._monitoring:
            if Organization.objects.filter(pk=organization.pk, monitoring = self._monitoring).count() < 1:
                raise forms.ValidationError(_("Illegal monitoring"));
        return organization

    class Meta:
        model = Task


class ParameterFilterForm(forms.Form):
    parameter = forms.ModelChoiceField(queryset = Parameter.objects.all(), label=_('parameter'))
    found = forms.IntegerField(min_value = 0, max_value = 1, label=_('found'))


class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim


class ClaimReportForm(forms.Form):
    expert = forms.ModelChoiceField(queryset = User.objects.all(), label=_('expert'))
    from_date = forms.DateTimeField(label=_('from date'),
        widget=widgets.AdminSplitDateTime,
        input_formats=DATETIME_INPUT_FORMATS)
    to_date = forms.DateTimeField(label=_('to date'),
        widget=widgets.AdminSplitDateTime,
        input_formats=DATETIME_INPUT_FORMATS)


class MonitoringForm(forms.ModelForm):
    status = forms.ChoiceField(choices=Monitoring.MONITORING_STATUS_FULL,
        label=_('status'))
    add_questionnaire = forms.BooleanField(required=False,
        label=_('Add questionnaire'))
    class Meta:
        model = Monitoring

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
    def get_queryset(self):
        if not hasattr(self, '_queryset'):
            self._queryset = self.queryset.filter(
                status__in=Monitoring.MONITORING_EDIT_STATUSES.keys()
            )
        return self._queryset


class MonitoringStatusForm(forms.ModelForm):
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
    def __init__(self, *args, **kwargs):
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
    def __init__(self, *args, **kwargs):
        self.monitoring = kwargs.pop('monitoring', None)
        super(MonitoringCommentStatForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        if not MonitoringStatus.objects.get(monitoring = self.monitoring, status = Monitoring.MONITORING_INTERACT).start:
            raise forms.ValidationError(_('Monitoring interact start date is missing. Check your monitoring calendar'))
        return cleaned_data

    limit = forms.IntegerField(min_value = 1, max_value = 10, label = _('time limit (in days)'), initial = 2)


class MonitoringRatingMultiple(forms.Form):
    monitoring = forms.ModelMultipleChoiceField(
        queryset = Monitoring.objects.all(),
        label =_('monitorings'),
        widget = widgets.FilteredSelectMultiple('',is_stacked=False),
    )


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
                    required=False, queryset=q.answervariant_set.order_by('-pk'),
                    widget=forms.RadioSelect(attrs={'class': 'aqchoice',}))

    def clean(self):
        cleaned_data = self.cleaned_data
        for answ in cleaned_data.items():
            if answ[0].startswith("q_") and not answ[1]\
               and self.task and self.task.approved:
                raise forms.ValidationError(_('Cannot delete answer for '
                                              'approved task. Edit answer instead.'))
        return cleaned_data


class BaseUserSettingsForm(forms.Form):
    """
    Базовая форма настроек пользователя."""
    first_name = forms.CharField(label=_("First name"),
        widget=forms.TextInput(attrs={"maxlength": 14}),
        required=False, max_length=14)
    patronymic = forms.CharField(label=_("Patronymic"),
        widget=forms.TextInput(attrs={"maxlength": 14}),
        required=False, max_length=14)
    last_name = forms.CharField(label=_("Last name"),
        widget=forms.TextInput(attrs={"maxlength": 30}),
        required=False, max_length=30)
    sex = forms.ChoiceField(label=_("Sex"), choices=SEX_CHOICES,
        widget=forms.RadioSelect(), required=False)
    old_password = forms.CharField(label=_("Current password"),
        widget=forms.PasswordInput(attrs={"maxlength": 24},
            render_value=False), required=False)
    new_password = forms.CharField(label=_("New password"),
        widget=forms.PasswordInput(attrs={"maxlength": 24},
            render_value=False), required=False)
    subscribe = forms.BooleanField(label="",
        help_text=_("Subscribe to news e-mail notification"), required=False)

    def clean(self):
        cd = self.cleaned_data
        email = cd.get("email")
        new_password = cd.get("new_password")
        # Требуется текущий пароль для смены email.
        if email and email != self.user.email:
            if not self.user.check_password(cd.get("old_password")):
                raise forms.ValidationError(
                    _("Current password required to change e-mail."))
            # Требуется текущий пароль для установки нового.
        if (new_password and
            not self.user.check_password(cd.get("old_password"))):
            raise forms.ValidationError(
                _("Current password required to set the new one."))
        return cd

    def clean_new_password(self):
        """Проверка пароля на наличие недопустимых символов."""
        password = self.cleaned_data.get('new_password', '')
        for char in password:  # Проверять на наличие пароля необязательно.
            if char not in PASSWORD_ALLOWED_CHARS:
                raise forms.ValidationError(_("Password contains unallowed "
                                              "characters. Please use only latin letters and digits."))
        return password

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(BaseUserSettingsForm, self).__init__(*args, **kwargs)


@autostrip
class OrdinaryUserSettingsForm(BaseUserSettingsForm):
    """Форма настроек обычного пользователя."""
    invitation_code = forms.CharField(label=_("Invitation code"),
        widget=forms.TextInput(attrs={"maxlength": 6}),
        required=False, max_length=6, min_length=6)


@autostrip
class OurUserSettingsForm(BaseUserSettingsForm):
    """Форма настроек нашего сотрудника."""
    comment_notification_type = forms.ChoiceField(
        choices=COMMENT_NOTIFICATION_CHOICES,
        label =_('Comment notification'), required = False)
    comment_notification_digest = forms.ChoiceField(choices=DIGEST_INTERVALS,
        required=False)
    notify_on_my_comments = forms.ChoiceField(
        choices=YES_NO_CHOICES, label=_('Send to me my comments'),
        required = False, widget = forms.RadioSelect())
    score_notification_type = forms.ChoiceField(
        choices=SCORE_CHANGE_NOTIFICATION_CHOICES,
        label=_('Score change notification'), required = False)
    score_notification_digest = forms.ChoiceField(choices=DIGEST_INTERVALS,
        required=False)


@autostrip
class OrgUserSettingsForm(OurUserSettingsForm):
    """Форма настроек представителя организации."""
    position = forms.CharField(label=_("Seat"),
        widget=forms.TextInput(attrs={"maxlength": 48}),
        required=False, max_length=48)
    phone = forms.CharField(label=_("Phone"),
        widget=forms.TextInput(attrs={"maxlength": 30}),
        required=False, max_length=30)


@autostrip
class OrgUserInfoForm(forms.Form):
    """Форма ввода доп. данных представителя организации."""
    position = forms.CharField(label=_("Seat"),
        widget=forms.TextInput(attrs={"maxlength": 48}),
        required=False, max_length=48)
    phone = forms.CharField(label=_("Phone"),
        widget=forms.TextInput(attrs={"maxlength": 30}),
        required=False, max_length=30)


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
    monitoring = forms.ModelChoiceField(
        queryset = Monitoring.objects.filter(status=Monitoring.MONITORING_PUBLISH).extra(select={
                'start_date': Monitoring().prepare_date_sql_inline(Monitoring.MONITORING_PUBLISH),
            }).order_by('-start_date'),
        required=False,
        empty_label=_('monitoring not select'),
        )
