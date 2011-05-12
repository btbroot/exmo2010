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
from django import forms
from django.utils.safestring import mark_safe
from exmo.exmo2010.models import Score, Task
from exmo.exmo2010.models import Parameter
from exmo.exmo2010.models import Claim
from exmo.exmo2010.models import Monitoring
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.translation import ugettext as _


class HorizRadioRenderer(forms.RadioSelect.renderer):
    """ this overrides widget method to put radio buttons horizontally
        instead of vertically.
    """
    def render(self):
            """Outputs radios"""
            return mark_safe(u'\n'.join([u'%s\n' % w for w in self]))


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
    def clean_user(self):
        user = self.cleaned_data['user']
        user_obj=User.objects.filter(username=user, is_active=True)
        if not user_obj:
            raise forms.ValidationError(_("This user account is inactive"));
        return user

    class Meta:
        model = Task



class UserForm(forms.ModelForm):
    notify_score_change = forms.BooleanField(required = False, label=_('notify score change'))

    class Meta:
        model = User
        exclude = (
            'username',
            'password',
            'groups',
            'user_permissions',
            'is_staff',
            'is_active',
            'is_superuser',
            'last_login',
            'date_joined'
        )



class ParameterFilterForm(forms.Form):
    parameter = forms.ModelChoiceField(queryset = Parameter.objects.all(), label=_('parameter'))
    found = forms.IntegerField(min_value = 0, max_value = 1, label=_('found'))



class ClaimForm(forms.ModelForm):
    open_task = forms.BooleanField(required = False, label=_('Open task'))
    class Meta:
        model = Claim



from django.contrib.admin import widgets
from django.conf import settings
class ClaimReportForm(forms.Form):
    def _media(self):
        js_tuple = (
                settings.ADMIN_MEDIA_PREFIX + 'js/core.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/admin/RelatedObjectLookups.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/jquery.min.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/jquery.init.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/actions.min.js',
             )
        js=base=forms.Media(js=js_tuple)
        for f in self.fields:
            js = base + self.fields[f].widget.media
        return js
    media = property(_media)

    expert = forms.ModelChoiceField(queryset = User.objects.all(), label=_('expert'))
    from_date = forms.DateTimeField(label=_('from date'), widget=widgets.AdminSplitDateTime)
    to_date = forms.DateTimeField(label=_('to date'), widget=widgets.AdminSplitDateTime)



from django.contrib.admin import widgets
class MonitoringForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        _monitoring = kwargs.get('instance')
        super(MonitoringForm, self).__init__(*args, **kwargs)
        initial = {}
        #if _monitoring:
        #    for p in ParameterMonitoringProperty.objects.filter(monitoring = _monitoring):
        #        initial[p.parameter.pk] = True
        self.fields['parameters'].initial = initial

    def _media(self):
        js_tuple = (
                settings.ADMIN_MEDIA_PREFIX + 'js/core.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/admin/RelatedObjectLookups.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/jquery.min.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/jquery.init.js',
                settings.ADMIN_MEDIA_PREFIX + 'js/actions.min.js',
             )
        js=forms.Media(js=js_tuple)
        for f in self.fields:
            js = js + self.fields[f].widget.media
        return js
    media = property(_media)

    publish_date = forms.DateField(required = False, widget=widgets.AdminDateWidget)
    parameters = forms.ModelMultipleChoiceField(
            queryset = Parameter.objects.all(),
            widget=widgets.FilteredSelectMultiple('',is_stacked=False),
        )

    class Meta:
        model = Monitoring



class ParameterForm(forms.ModelForm):
    class Meta:
        model = Parameter
        exclude = ('monitoring',)
