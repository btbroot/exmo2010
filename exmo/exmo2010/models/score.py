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
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _

from core.utils import clean_message

from .base import BaseModel
from .claim import Claim
from .clarification import Clarification
from .parameter import Parameter


class Score(BaseModel):
    """
    Модель оценки
    """

    class Meta(BaseModel.Meta):
        unique_together = (('task', 'parameter', 'revision'),)
        ordering = (
            'task__user__username',
            'task__organization__name',
            'parameter__code'
        )

    REVISION_DEFAULT = 0
    REVISION_INTERACT = 1

    REVISION_EXPORT = {
        REVISION_DEFAULT: 'default',
        REVISION_INTERACT: 'initial',
    }

    REVISION_CHOICE = (
        (REVISION_DEFAULT, _('latest revision')),
        (REVISION_INTERACT, _('pre-interact revision')),
    )

    task = models.ForeignKey("Task", verbose_name=_('task'))
    parameter = models.ForeignKey("Parameter", verbose_name=_('parameter'))

    _01 = ((0, 0), (1, 1))
    _123 = ((1, 1), (2, 2), (3, 3))

    found = models.IntegerField(choices=_01, verbose_name=_('Found'))
    complete = models.IntegerField(null=True, blank=True, choices=_123, verbose_name=_('Complete'))
    topical = models.IntegerField(null=True, blank=True, choices=_123, verbose_name=_('Topical'))
    accessible = models.IntegerField(null=True, blank=True, choices=_123, verbose_name=_('Accessible'))
    hypertext = models.IntegerField(null=True, blank=True, choices=_01, verbose_name=_('Hypertext'))
    document = models.IntegerField(null=True, blank=True, choices=_01, verbose_name=_('Document'))
    image = models.IntegerField(null=True, blank=True, choices=_01, verbose_name=_('Image'))

    links = models.TextField(null=True, blank=True, verbose_name=_('Links'))
    recommendations = models.TextField(null=True, blank=True, verbose_name=_('Recommendations'))
    created = models.DateTimeField(auto_now_add=True, null=True)
    last_modified = models.DateTimeField(auto_now=True, null=True)
    editor = models.ForeignKey(User, null=True, blank=True, verbose_name=_('Editor'))
    revision = models.PositiveIntegerField(default=REVISION_DEFAULT, choices=REVISION_CHOICE)
    accomplished = models.BooleanField(default=True)

    def __unicode__(self):
        return '%s: %s [%d]' % (
            self.task.user.username,
            self.task.organization.name,
            self.parameter.code
        )

    def criteria(self):
        for crit in Parameter.OPTIONAL_CRITERIONS:
            if getattr(self.parameter, crit):
                yield getattr(self, crit)
            else:
                yield None

    def clean(self):
        # Relevant criteria
        criteria = ['found'] + filter(self.parameter.__getattribute__, Parameter.OPTIONAL_CRITERIONS)

        # If found == 1, all relevant criteria should be non-null
        if self.found:
            for crit in criteria:
                if getattr(self, crit) in ('', None):
                    name = self._meta.get_field(crit).verbose_name
                    raise ValidationError(ugettext('%(criterion)s must be set') % {'criterion': name})

        all_max = all(getattr(self, c) == self._meta.get_field(c).choices[-1][-1] for c in criteria)

        if not all_max:
            # If score is not maximum, recommendations should not be empty.
            if not self.recommendations:
                raise ValidationError(ugettext('Score is not maximum, recommendations should exist'))

            # If score changed, recommendations should change too.
            # BUG 2069: If score is maximum, we should omit this check, because there will be old scores
            # in database, which have empty recommendations, but rated to non-maximum. Reevaluating those
            # scores to maximum should be possible, even if recommendations does not change (empty).
            if self.pk:
                db_score = Score.objects.get(pk=self.pk)
                if self.recommendations == db_score.recommendations:
                    for crit in criteria:
                        if getattr(self, crit) != getattr(db_score, crit):
                            raise ValidationError(ugettext('Recommendations should change when score is changed'))

    def unique_error_message(self, model_class, unique_check):
        # A unique field
        if len(unique_check) == 1:
            result = super(Score, self).unique_error_message(model_class, unique_check)
        # unique_together
        else:
            result = ugettext(u"A technical error of scores evaluation. To edit the score start from the go back "
                              u"to task page and skip to page of parameter evaluation by link from score table.")

        return result

    def save(self, *args, **kwargs):
        if self.pk is not None:
            self.accomplished = True

        # If found == 0, reset all criteria to NULL. This is required in this scenario:
        # 1) ExpertB creates score with some criterion set to non-zero.
        # 2) ExpertA marks criterion as non-relevant.
        # 3) ExpertB reconsiders score and chages it to all-zero (found=0)
        # 4) ExpertA marks criterion back as relevant.
        # -- At this point criterion should be rated as zero regardless of its initial value at
        #    point 1, because found is zero.
        if not self.found:
            for crit in self.parameter.OPTIONAL_CRITERIONS:
                setattr(self, crit, None)

        super(Score, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('exmo2010:score_view', [str(self.id)])

    @property
    def openness(self):
        complete = 1
        topical = 1
        accessible = 1
        hypertext = 1
        document = 1
        image = 1
        param = self.parameter

        if param.complete:
            if self.complete == 1:
                complete = 0.2
            elif self.complete == 2:
                complete = 0.5

        if param.topical:
            if self.topical == 1:
                topical = 0.7
            elif self.topical == 2:
                topical = 0.85

        if param.accessible:
            if self.accessible == 1:
                accessible = 0.9
            elif self.accessible == 2:
                accessible = 0.95

        if param.hypertext and self.hypertext == 0:
            hypertext = 0.2

        if param.document and self.document == 0:
            document = 0.85

        if param.image and self.image == 0:
            image = 0.95

        result = self.found * complete * topical * accessible * hypertext * document * image * 100.0

        return result

    def add_clarification(self, creator, comment):
        clarification = Clarification(score=self, creator=creator, comment=clean_message(comment))
        clarification.save()
        return clarification

    def add_claim(self, creator, comment):
        claim = Claim(score=self, creator=creator, comment=clean_message(comment))
        claim.addressee = claim.score.task.user
        claim.full_clean()
        claim.save()
        return claim

    def claim_color(self):
        """
        Return the color of the claim`s icon.

        """
        color = None

        claims = Claim.objects.filter(score=self, addressee=self.task.user)
        open_claims = claims.filter(close_date__isnull=True)

        if claims:
            color = 'green'
            if open_claims:
                color = 'red'

        return color
