from django import forms
from django.utils.safestring import mark_safe
from exmo.exmo2010.models import Score, Task
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
