# -*- coding: utf-8 -*-
from digest_email.digest import DigestSend
from digest_email import models as digest_models
from datetime import datetime
from django.contrib.comments.models import Comment
from exmo2010.models import Score

class ScoreCommentDigest(DigestSend):

    def get_content(self, user, timestamp = datetime.now()):
        "Собираем комментарии для отправления с момента последней отправки дайджеста по timestamp"

        if user.userprofile.is_expertA or user.userprofile.is_manager_expertB:
            score_pk = Score.objects.all()
        elif user.userprofile.is_expertB:
            score_pk = Score.objects.filter(task__user = user)
        elif user.userprofile.is_organization:
            score_pk = Score.objects.filter(task__organization__in = user.userprofile.organization)
        else:
            score_pk = Score.objects.none()

        last_digest_date = self.digest.get_last(user)
        qs = Comment.objects.filter(
            content_type__model = 'score',
            object_pk__in = score_pk.values_list('id', flat=True),
        ).order_by('submit_date')

        if last_digest_date:
            qs = qs.filter(submit_date__gte = last_digest_date)
        if not user.userprofile.notify_comment_preference['self']:
            qs = qs.exclude(user = user)
        return qs
