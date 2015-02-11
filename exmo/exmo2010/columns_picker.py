# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014-2015 IRSI LTD
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
from django.db.models import Model, BooleanField
from django.forms.models import modelform_factory
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy


class ColumnsPickerModel(Model):
    class Meta:
        abstract = True

    # Rating table columns
    rt_representatives = BooleanField(verbose_name=pgettext_lazy(u'number of representatives', u'Representatives'), default=True)
    rt_comment_quantity = BooleanField(verbose_name=_("Comment quantity"), default=True)
    rt_initial_openness = BooleanField(verbose_name=_("Initial Openness"), default=False)
    rt_final_openness = BooleanField(verbose_name=_("Final Openness"), default=True)
    rt_difference = BooleanField(verbose_name=_("Difference"), default=True)

    RATING_COLUMNS_FIELDS = 'rt_initial_openness rt_final_openness rt_difference rt_representatives rt_comment_quantity'.split()

    # Task-scores table columns
    st_criteria = BooleanField(verbose_name=_("Criteria"), default=True)
    st_score = BooleanField(verbose_name=_("Score"), default=True)
    st_difference = BooleanField(verbose_name=_("Difference"), default=True)
    st_weight = BooleanField(verbose_name=_("Weight"), default=False)
    st_type = BooleanField(verbose_name=_("Type"), default=False)

    TASKSCORES_COLUMNS_FIELDS = 'st_criteria st_score st_difference st_weight st_type'.split()

    # Monitoring dates table columns
    mon_evaluation_start = BooleanField(verbose_name=_("Eval. start"), default=True)
    mon_interact_start = BooleanField(verbose_name=_("Interact start"), default=True)
    mon_interact_end = BooleanField(verbose_name=_("Interact end"), default=True)
    mon_publish_date = BooleanField(verbose_name=_("Publish date"), default=True)

    MONITORINGS_INDEX_COLUMNS_FIELDS = 'mon_evaluation_start mon_interact_start mon_interact_end mon_publish_date'.split()


class ColumnsPickerForm(forms.ModelForm):
    """
    This form will be a base for concrete form, holding fields corresponding to columns of displayed table.
    Each pickable column will have associated boolean field, with value of True meaning that column is visible.

    This form introduces "forbidden" fields (columns). Those fields value will always be "False".
    To ease template rendering, forbidden fields are excluded when iterating over the form.
    """

    def __init__(self, *args, **kwargs):
        """
        If `forbidden_columns` kwarg is provided, it should be a list of field names.
        """
        self.forbidden_columns = kwargs.pop('forbidden_columns', [])
        super(ColumnsPickerForm, self).__init__(*args, **kwargs)
        self.data = dict(self.data)  # convert immutable request data to dict
        for column in self.forbidden_columns:
            self.data[column] = False
            self.initial[column] = False

    def __iter__(self):
        """
        Exclude forbidden columns from list of all fields when iterating.
        """
        for name in self.fields:
            if name not in self.forbidden_columns:
                yield self[name]

    def post_ok(self, request):
        """
        Check if form was submitted and save changes in database.
        """
        if request.method == 'POST' and 'columns_picker_submit' in request.POST:
            # Form was submitted.
            if self.instance.pk and self.is_valid():
                # Save changes in UserProfile.
                self.save()
            return True
        else:
            return False


def rating_columns_form(request):
    from .models import UserProfile
    RatingColumnsForm = modelform_factory(UserProfile, form=ColumnsPickerForm,
                                          fields=UserProfile.RATING_COLUMNS_FIELDS)

    if request.user.is_active:
        if request.method == 'POST' and 'columns_picker_submit' in request.POST:
            data = request.POST
        else:
            data = None

        if request.user.is_expert:
            forbidden_columns = []
        else:
            forbidden_columns = ['rt_representatives', 'rt_comment_quantity']

        return RatingColumnsForm(data, instance=request.user.profile, forbidden_columns=forbidden_columns)
    else:
        # Inactive or anonymous user will always see only rt_final_openness and rt_difference.
        data = {
            'rt_difference': True,
            'rt_final_openness': True,
            'rt_representatives': False,
            'rt_comment_quantity': False,
            'rt_initial_openness': False
        }
        return RatingColumnsForm(data)


def task_scores_columns_form(request):
    from .models import UserProfile
    ScoresColumnsForm = modelform_factory(UserProfile, form=ColumnsPickerForm,
                                          fields=UserProfile.TASKSCORES_COLUMNS_FIELDS)

    if request.user.is_expert:
        if request.method == 'POST' and 'columns_picker_submit' in request.POST:
            data = request.POST
        else:
            data = None

        return ScoresColumnsForm(data, instance=request.user.profile)
    else:
        # Non-expert user will always see only st_score, st_difference and st_type.
        data = {
            'st_criteria': False,
            'st_score': True,
            'st_difference': True,
            'st_weight': False,
            'st_type': True
        }
        return ScoresColumnsForm(data)


def monitorings_index_columns_form(request):
    from .models import UserProfile
    MonitoringsIndexColumnsForm = modelform_factory(UserProfile, form=ColumnsPickerForm,
                                                    fields=UserProfile.MONITORINGS_INDEX_COLUMNS_FIELDS)

    if request.method == 'POST' and 'columns_picker_submit' in request.POST:
        data = request.POST
    else:
        data = None

    return MonitoringsIndexColumnsForm(data, instance=request.user.profile)
