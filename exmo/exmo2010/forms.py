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
from django import forms
from django.utils.safestring import mark_safe
from exmo2010.models import Score, Task
from exmo2010.models import Parameter
from exmo2010.models import Claim
from exmo2010.models import Monitoring
from exmo2010.models import MonitoringStatus
from exmo2010.models import Organization
from exmo2010.models import UserProfile
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.admin import widgets
from exmo2010.widgets import TagAutocomplete

CORE_JS = (
                settings.ADMIN_MEDIA_PREFIX + 'js/core.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/admin/RelatedObjectLookups.js',
                settings.STATIC_URL + 'exmo2010/js/jquery/jquery.min.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/jquery.init.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/actions.min.js',
          )

CORE_MEDIA = forms.Media(js=CORE_JS)



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



from exmo2010.stackedform import StackedForm
class UserForm(forms.ModelForm, StackedForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    form_template  = 'exmo2010/forms/stacked_form.html'
    field_template = 'exmo2010/forms/stack_field.html'

    class Stack:
        stack = (
            {
                'label': _('User information'),
                'fields': ('first_name', 'last_name', 'email'),
            },
        )


class UserProfileForm(forms.ModelForm, StackedForm):
    comment_notification_type = forms.ChoiceField(
        choices = UserProfile.NOTIFICATION_TYPE_CHOICES,
        label = _('notification type'),
        required = False,
        widget = forms.RadioSelect(),
    )

    comment_notification_digest = forms.IntegerField(label = _('digest interval (in hours)'), required = False, min_value = 1, max_value = 24)

    comment_notification_self = forms.BooleanField(
        label = _('send to me my comments'),
        required = False,
    )

    score_notification_type = forms.ChoiceField(
        choices = UserProfile.NOTIFICATION_TYPE_CHOICES,
        label = _('notification type'),
        required = False,
        widget = forms.RadioSelect(),
    )

    score_notification_digest = forms.IntegerField(label = _('digest interval (in hours)'), required = False, min_value = 1, max_value = 24)

    form_template  = 'exmo2010/forms/stacked_form.html'
    field_template = 'exmo2010/forms/stack_field.html'

    class Stack:
      stack = (
        {
            'label': _('Sex'),
            'fields': ('sex',),
        },
        {
            'label': _('Comment notification'),
            'fields': ('comment_notification_type','comment_notification_digest','comment_notification_self'),
        },
        {
            'label': _('Score change notification'),
            'fields': ('score_notification_type','score_notification_digest'),
        }
      )

    class Meta:
        model = UserProfile
        exclude = ["user", "organization", "preference"]

    def __init__(self, *args, **kwargs):
        profile = kwargs.get('instance')
        super(UserProfileForm, self).__init__(*args, **kwargs)
        score_pref = profile.notify_score_preference
        comment_pref = profile.notify_comment_preference

        self.fields['comment_notification_type'].initial = comment_pref['type']
        self.fields['comment_notification_self'].initial = comment_pref['self']
        self.fields['comment_notification_digest'].initial = comment_pref['digest_duratation']

        self.fields['score_notification_type'].initial = score_pref['type']
        self.fields['score_notification_digest'].initial = score_pref['digest_duratation']

    def clean_comment_notification_digest(self):
        if self.cleaned_data['comment_notification_type'] == str(UserProfile.NOTIFICATION_TYPE_DIGEST) \
          and not self.cleaned_data['comment_notification_digest']:
            raise forms.ValidationError(_("Must be filled if you select digest notification"))
        return self.cleaned_data['comment_notification_digest']

    def clean_score_notification_digest(self):
        if self.cleaned_data['score_notification_type'] == str(UserProfile.NOTIFICATION_TYPE_DIGEST) \
          and not self.cleaned_data['score_notification_digest']:
            raise forms.ValidationError(_("Must be filled if you select digest notification"))
        return self.cleaned_data['score_notification_digest']

    def save(self, force_insert=False, force_update=False, commit=True):
        profile = super(UserProfileForm, self).save(commit=False)
        comment_pref = {
            'type': self.cleaned_data['comment_notification_type'],
            'self': self.cleaned_data['comment_notification_self'],
            'digest_duratation': self.cleaned_data['comment_notification_digest'],
        }
        score_pref = {
            'type': self.cleaned_data['score_notification_type'],
            'digest_duratation': self.cleaned_data['score_notification_digest'],
        }

        profile.notify_comment_preference = comment_pref
        profile.notify_score_preference = score_pref

        if commit:
            profile.save()



class ParameterFilterForm(forms.Form):
    parameter = forms.ModelChoiceField(queryset = Parameter.objects.all(), label=_('parameter'))
    found = forms.IntegerField(min_value = 0, max_value = 1, label=_('found'))



class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim



class ClaimReportForm(forms.Form):
    expert = forms.ModelChoiceField(queryset = User.objects.all(), label=_('expert'))
    from_date = forms.DateTimeField(label=_('from date'), widget=widgets.AdminSplitDateTime)
    to_date = forms.DateTimeField(label=_('to date'), widget=widgets.AdminSplitDateTime)



class MonitoringForm(forms.ModelForm):
    status = forms.ChoiceField(choices=Monitoring.MONITORING_STATUS_FULL,
        label=_('status'))
    add_questionnaire = forms.BooleanField(required=False,
        label=_('Add questionnaire'))
    class Meta:
        model = Monitoring



class MonitoringStatusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        ms = kwargs.get('instance')
        super(MonitoringStatusForm, self).__init__(*args, **kwargs)
        self.fields['status'].choices = ((ms.status, ms),)

    class Meta:
        model = MonitoringStatus
        widgets = {
            'start':widgets.AdminSplitDateTime,
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
        widgets = {
            'keywords': TagAutocomplete,
        }


class MonitoringCommentStatForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.monitoring = kwargs.get('monitoring')
        if self.monitoring:
            kwargs.pop('monitoring')
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
