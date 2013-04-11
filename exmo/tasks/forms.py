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
from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _

from exmo2010.models import Organization, Task, TaskHistory, UserProfile


class TaskForm(forms.ModelForm):
    """
    Форма редактирования/создания задачи.

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
        self.fields['user'].queryset = User.objects.filter(groups__name__in=UserProfile.expert_groups,
                                                           is_active=True).distinct()
        if self._monitoring:
            self.fields['organization'].queryset = Organization.objects.filter(monitoring=self._monitoring)

    def clean_user(self):
        """
        Проверка на активность пользователя которому была назначена задача.

        """
        user = self.cleaned_data['user']
        user_obj = User.objects.filter(username=user, is_active=True)
        if not user_obj:
            raise forms.ValidationError(_("This user account is inactive"))
        return user

    def clean_organization(self):
        """
        Проверка на соответствие мониторинга.

        """
        organization = self.cleaned_data['organization']
        if self._monitoring:
            if Organization.objects.filter(pk=organization.pk, monitoring=self._monitoring).count() < 1:
                raise forms.ValidationError(_("Illegal monitoring"))
        return organization

    def save(self, *args, **kwargs):
        """
        Saves the new task history if expert was changed.

        """
        task = self.instance.id

        if task:
            user = Task.objects.get(pk=task).user
            task_id = super(TaskForm, self).save(*args, **kwargs)

            if user == task_id.user:
                return task_id

        else:
            task_id = super(TaskForm, self).save(*args, **kwargs)

        TaskHistory.objects.create(
            task=task_id,
            user=self.cleaned_data['user'],
            status=self.cleaned_data['organization'].monitoring.status
        )

        return task_id

    class Meta:
        model = Task
