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

from django.db import models
from django.utils.translation import ugettext as _

from .base import BaseModel


# Типы вопросов анкеты. Добавить переводы!
QUESTION_TYPE_CHOICES = (
    (0, _("Text")),
    (1, _("Number")),
    (2, _("Choose a variant")),
)


class Questionnaire(BaseModel):
    """Анкета, привязанная к мониторингу"""
    monitoring = models.ForeignKey("Monitoring", verbose_name=_("Monitoring"), unique=True)
    title = models.CharField(max_length=300, verbose_name=_("Questionnaire name"), blank=True)
    comment = models.CharField(max_length=600, verbose_name=_("Questionnaire comment"), blank=True)

    def __unicode__(self):
        return '%s' % self.monitoring.__unicode__()


class QQuestion(BaseModel):
    """Вопрос анкеты, привязанной к мониторингу"""
    questionnaire = models.ForeignKey("Questionnaire", verbose_name=_("Questionnaire"))
    qtype = models.PositiveSmallIntegerField(choices=QUESTION_TYPE_CHOICES, verbose_name=_("Question type"))
    question = models.CharField(_("Question"), max_length=300)
    comment = models.CharField(_("Question comment"), max_length=600, blank=True)

    def __unicode__(self):
        return '%s: %s' % (self.questionnaire.__unicode__(), self.question)


class AnswerVariant(BaseModel):
    """Вариант ответа на вопрос анкеты, предполагающий варианты"""
    qquestion = models.ForeignKey(QQuestion, verbose_name=_("Question"))
    answer = models.CharField(_("Answer"), max_length=300)

    def __unicode__(self):
        return self.answer


class QAnswer(BaseModel):
    """Ответ на вопрос анкеты"""
    class Meta(BaseModel.Meta):
        unique_together = ('task', 'question')

    task = models.ForeignKey("Task")
    question = models.ForeignKey(QQuestion, verbose_name=_("Question"))
    text_answer = models.CharField(_("Text answer"), max_length=300, blank=True)
    numeral_answer = models.PositiveIntegerField(_("Numerical answer"), blank=True, null=True)
    variance_answer = models.ForeignKey(AnswerVariant, verbose_name=_("Variance choice"), blank=True, null=True)

    def answer(self, for_form=False):
        if self.question.qtype == 0:
            return self.text_answer
        elif self.question.qtype == 1:
            return self.numeral_answer
        elif self.question.qtype == 2:
            if self.variance_answer:
                if for_form:
                    return self.variance_answer
                else:
                    return self.variance_answer.answer
            else:
                return None

    def __unicode__(self):
        return '%s: %s' % (self.task.__unicode__(),
                           self.question.__unicode__())
