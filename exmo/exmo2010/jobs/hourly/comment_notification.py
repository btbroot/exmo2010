"""
Daily cleanup job.

Can be run as a cronjob to send comment digest
"""

from django_extensions.management.jobs import DailyJob


class Job(DailyJob):
    help = "Comment daily digest notification"

    def execute(self):
        from exmo2010.digest import ScoreCommentDigest
        from digest_email.models import Digest
        digest = ScoreCommentDigest(Digest.objects.get(name = 'notify_comment'))
        digest.send()
