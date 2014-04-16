# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
from ckeditor.fields import RichTextField
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .base import BaseModel


class Parameter(BaseModel):

    class Meta(BaseModel.Meta):
        ordering = ('code', 'name')
        unique_together = tuple(('name_%s' % lang[0], 'monitoring') for lang in settings.LANGUAGES) + (('code', 'monitoring'),)

    code = models.PositiveIntegerField(verbose_name=_('code'))
    name = models.CharField(max_length=1000, verbose_name=_('name'))
    grounds = RichTextField(blank=True, config_name='advanced', verbose_name=_('grounds'))
    rating_procedure = RichTextField(blank=True, config_name='advanced', verbose_name=_('rating procedure'))
    notes = RichTextField(blank=True, config_name='advanced', verbose_name=_('notes'))

    # Set editable=False attribute on "monitoring".
    # This is workaround for Django bug 13091 https://code.djangoproject.com/ticket/13091
    # See note on ParamEditView.get_form_class() method
    monitoring = models.ForeignKey("Monitoring", verbose_name=_('monitoring'), editable=False)
    exclude = models.ManyToManyField("Organization", null=True, blank=True, verbose_name=_('excluded organizations'))
    weight = models.IntegerField(verbose_name=_('weight'))

    complete = models.BooleanField(default=True, verbose_name=_('complete'))
    topical = models.BooleanField(default=True, verbose_name=_('topical'))
    accessible = models.BooleanField(default=True, verbose_name=_('accessible'))
    hypertext = models.BooleanField(default=True, verbose_name=_('hypertext'))
    document = models.BooleanField(default=True, verbose_name=_('document'))
    image = models.BooleanField(default=True, verbose_name=_('image'))
    npa = models.BooleanField(default=False, verbose_name=_('normative parameter'))

    #необязательные критерии в оценке
    OPTIONAL_CRITERIONS = [
        'complete',
        'topical',
        'accessible',
        'hypertext',
        'document',
        'image'
    ]

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        from .score import Score

        if self.pk is None:
            super(Parameter, self).save(*args, **kwargs)
        else:
            before = Parameter.objects.filter(pk=self.pk).values_list(*Parameter.OPTIONAL_CRITERIONS)[0]
            after = tuple(getattr(self, i) for i in Parameter.OPTIONAL_CRITERIONS)
            super(Parameter, self).save(*args, **kwargs)

            if (False, True) in zip(before, after):
                # Unset accomplished flag on all scores
                self.score_set.filter(found=1, revision=Score.REVISION_DEFAULT, accomplished=True)\
                              .update(accomplished=False)

            # Restore accomplished flag on scores that already have non-null relevant criteria
            # This happens in two cases of criterion relevance changing.
            # First case:
            # 1) Given criterion initial relevance is False
            # 2) Score added
            # 3) Relevance changed to True - Score "accomplished" flag unset.
            # 4) Relevance changed back to False
            # -- Score should become accomplished again, because all currently relevant criteria was initially rated.
            #
            # Second case:
            # 1) Given criterion initial relevance is True
            # 2) Score added
            # 3) Relevance changed to False
            # 4) Relevance changed back to True - Score "accomplished" flag unset.
            # -- Score should become accomplished again, because this criterion was initially rated.
            scores = self.score_set.filter(found=1, revision=Score.REVISION_DEFAULT)
            for criterion in Parameter.OPTIONAL_CRITERIONS:
                if getattr(self, criterion) is True:
                    # Criterion is relevant
                    scores = scores.filter(**{criterion + '__isnull': False})
            scores.update(accomplished=True)
