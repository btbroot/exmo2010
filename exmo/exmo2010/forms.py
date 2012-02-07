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
from exmo.exmo2010.models import Score, Task
from exmo.exmo2010.models import Parameter
from exmo.exmo2010.models import Claim
from exmo.exmo2010.models import Monitoring
from exmo.exmo2010.models import MonitoringStatus
from exmo.exmo2010.models import Organization
from exmo.exmo2010.models import UserProfile
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.admin import widgets
from exmo.exmo2010.widgets import TagAutocomplete

CORE_JS = (
                settings.ADMIN_MEDIA_PREFIX + 'js/core.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/admin/RelatedObjectLookups.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/jquery.min.js',
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



class TaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(groups__name__in = UserProfile.expert_groups, is_active = True)

    def clean_user(self):
        user = self.cleaned_data['user']
        user_obj=User.objects.filter(username=user, is_active=True)
        if not user_obj:
            raise forms.ValidationError(_("This user account is inactive"));
        return user

    class Meta:
        model = Task



class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]



class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        exclude = ["user", "organization"]



class ParameterFilterForm(forms.Form):
    parameter = forms.ModelChoiceField(queryset = Parameter.objects.all(), label=_('parameter'))
    found = forms.IntegerField(min_value = 0, max_value = 1, label=_('found'))



class ClaimForm(forms.ModelForm):
    open_task = forms.BooleanField(required = False, label=_('Open task'))
    class Meta:
        model = Claim



class ClaimReportForm(forms.Form):
    expert = forms.ModelChoiceField(queryset = User.objects.all(), label=_('expert'))
    from_date = forms.DateTimeField(label=_('from date'), widget=widgets.AdminSplitDateTime)
    to_date = forms.DateTimeField(label=_('to date'), widget=widgets.AdminSplitDateTime)



class MonitoringForm(forms.ModelForm):
    status = forms.ChoiceField(choices = Monitoring.MONITORING_STATUS_FULL, label=_('status'))
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
