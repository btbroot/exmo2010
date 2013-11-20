# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
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

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext as _

from core.utils import clean_message

from .base import BaseModel
from .claim import Claim
from .clarification import Clarification
from .monitoring import Monitoring


class Score(BaseModel):
    """
    Модель оценки
    """

    REVISION_DEFAULT = 0
    REVISION_INTERACT = 1

    REVISION_EXPORT = {
        REVISION_DEFAULT: 'default',
        REVISION_INTERACT: 'initial',
    }

    REVISION_CHOICE = (
        (REVISION_DEFAULT, _('default revision')),
        (REVISION_INTERACT, _('interact revision')),
    )

    task = models.ForeignKey("Task", verbose_name=_('task'))
    parameter = models.ForeignKey("Parameter", verbose_name=_('parameter'))

    found = models.IntegerField(
        choices=((0, 0), (1, 1)),
        verbose_name=_('found'),
    )
    foundComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('foundComment'),
    )
    complete = models.IntegerField(
        null=True,
        blank=True,
        choices=((1, 1), (2, 2), (3, 3)),
        verbose_name=_('complete'),
    )
    completeComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('completeComment'),
    )
    topical = models.IntegerField(
        null=True,
        blank=True,
        choices=((1, 1), (2, 2), (3, 3)),
        verbose_name=_('topical'),
    )
    topicalComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('topicalComment'),
    )
    accessible = models.IntegerField(
        null=True,
        blank=True,
        choices=((1, 1), (2, 2), (3, 3)),
        verbose_name=_('accessible'),
    )
    accessibleComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('accessibleComment'),
    )
    hypertext = models.IntegerField(
        null=True,
        blank=True,
        choices=((0, 0), (1, 1)),
        verbose_name=_('hypertext'),
    )
    hypertextComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('hypertextComment'),
    )
    document = models.IntegerField(
        null=True,
        blank=True,
        choices=((0, 0), (1, 1)),
        verbose_name=_('document'),
    )
    documentComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('documentComment'),
    )
    image = models.IntegerField(
        null=True,
        blank=True,
        choices=((0, 0), (1, 1)),
        verbose_name=_('image'),
    )
    imageComment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('imageComment'),
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Recomendations'),
    )
    created = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
    )
    edited = models.DateTimeField(
        null=True,
        blank=True,
        auto_now=True,
    )
    revision = models.PositiveIntegerField(
        default=REVISION_DEFAULT,
        choices=REVISION_CHOICE,
    )

    def __unicode__(self):
        return '%s: %s [%d]' % (
            self.task.user.username,
            self.task.organization.name,
            self.parameter.code
        )

    def clean(self):
        """
        Оценка не может быть заполнена частично
        В оценке не может быть оценено то,
        что не предусмотрено к оценке в параметре
        У оценки не может быть found=0 при не пустых прочих критериях
        """
        if self.found:
            if self.parameter.complete and self.complete in ('', None):
                raise ValidationError(_('Complete must be set'))
            if self.parameter.topical and self.topical in ('', None):
                raise ValidationError(_('Topical must be set'))
            if self.parameter.accessible and self.accessible in ('', None):
                raise ValidationError(_('Accessible must be set'))
            if self.parameter.hypertext and self.hypertext in ('', None):
                raise ValidationError(_('Hypertext must be set'))
            if self.parameter.document and self.document in ('', None):
                raise ValidationError(_('Document must be set'))
            if self.parameter.image and self.image in ('', None):
                raise ValidationError(_('Image must be set'))
        elif any((
                self.complete != None,
                self.topical != None,
                self.accessible != None,
                self.hypertext != None,
                self.document != None,
                self.image != None,
                self.completeComment,
                self.topicalComment,
                self.accessibleComment,
                self.hypertextComment,
                self.documentComment,
                self.imageComment)):
            raise ValidationError(_('Not found, but some excessive data persists'))

    def unique_error_message(self, model_class, unique_check):
        # A unique field
        if len(unique_check) == 1:
            result = super(Score, self).unique_error_message(model_class, unique_check)
        # unique_together
        else:
            result = _(u"A technical error of scores evaluation. To edit the score start from the task page.")

        return result

    @models.permalink
    def get_absolute_url(self):
        return ('exmo2010:score_view', [str(self.id)])

    def _get_claim(self):
        return Claim.objects.filter(score=self, close_date__isnull=True, addressee=self.task.user).exists()

    def _get_openness(self):
        return openness_helper(self)

    def add_clarification(self, creator, comment):
        """
        Добавляет уточнение
        """
        comment = clean_message(comment)
        clarification = Clarification(score=self,
                                      creator=creator,
                                      comment=comment)
        clarification.save()
        return clarification

    def add_claim(self, creator, comment):
        comment = clean_message(comment)
        claim = Claim(score=self, creator=creator, comment=comment)
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

    def create_revision(self, revision):
        """
        Создание ревизии оценки
        """
        if self.task.organization.monitoring.status in Monitoring.after_interaction_status \
           and revision == Score.REVISION_INTERACT:
            revision_score = Score.objects.filter(
                task=self.task,
                parameter=self.parameter,
                revision=revision,
            )
            if not revision_score and self.pk:
                revision_score = Score.objects.get(pk=self.pk)
                revision_score.pk = None
                revision_score.revision = revision
                revision_score.full_clean()
                revision_score.save()

    active_claim = property(_get_claim)
    openness = property(_get_openness)

    class Meta(BaseModel.Meta):
        unique_together = (('task', 'parameter', 'revision'),)
        ordering = (
            'task__user__username',
            'task__organization__name',
            'parameter__code'
        )


def openness_helper(score):
    """
    Помощник для вычисления Кид через SQL
    """
    sql = """
        SELECT
        %(score_openness)s
        FROM
        exmo2010_score
        join exmo2010_parameter on exmo2010_score.parameter_id=exmo2010_parameter.id
        where exmo2010_score.id=%(pk)d
    """ % {
        'pk': score.pk,
        'score_openness': score.task.organization.monitoring.openness_expression.get_sql_openness(),
    }
    s = Score.objects.filter(pk=score.pk).extra(select={
        'sql_openness': sql,
    })
    return float(s[0].score_openness)
