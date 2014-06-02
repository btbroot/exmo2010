# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
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
from south.v2 import DataMigration
from exmo2010.models import Parameter


class Migration(DataMigration):

    def forwards(self, orm):
        """
        Get all urls from '...Comment' fields and save it
        in 'links' field as plaintext.

        """
        fields = [field + 'Comment' for field in Parameter.OPTIONAL_CRITERIONS]

        scores = orm.Score.objects.filter(foundComment__isnull=False)
        for f in fields:
            scores |= orm.Score.objects.filter(**{'%s__isnull' % f: False})

        for score in scores:
            if score.foundComment is None:
                score.foundComment = ''
            for f in fields:
                if getattr(score, f):
                    score.foundComment += '\n%s' % getattr(score, f)

            score.save()

    def backwards(self, orm):
        """There are no backwards methods."""
        pass

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'exmo2010.answervariant': {
            'Meta': {'object_name': 'AnswerVariant'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'qquestion': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.QQuestion']"})
        },
        'exmo2010.claim': {
            'Meta': {'object_name': 'Claim'},
            'addressee': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'related_name': "'addressee'", 'to': "orm['auth.User']"}),
            'answer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'close_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'close_user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'close_user'", 'null': 'True', 'to': "orm['auth.User']"}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'creator'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'open_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'score': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Score']"})
        },
        'exmo2010.clarification': {
            'Meta': {'object_name': 'Clarification'},
            'answer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'close_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'close_user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'clarification_close_user'", 'null': 'True', 'to': "orm['auth.User']"}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clarification_creator'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'open_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'score': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Score']"})
        },
        'exmo2010.inviteorgs': {
            'Meta': {'object_name': 'InviteOrgs'},
            'comment': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inv_status': ('django.db.models.fields.CharField', [], {'default': "'ALL'", 'max_length': '3'}),
            'monitoring': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Monitoring']"}),
            'subject': ('django.db.models.fields.TextField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'exmo2010.monitoring': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Monitoring'},
            'finishing_date': ('django.db.models.fields.DateField', [], {}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interact_date': ('django.db.models.fields.DateField', [], {}),
            'map_link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_az': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name_en': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name_ka': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name_ru': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'no_interact': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'openness_expression': ('django.db.models.fields.related.ForeignKey', [], {'default': '8', 'to': "orm['exmo2010.OpennessExpression']"}),
            'publish_date': ('django.db.models.fields.DateField', [], {}),
            'rate_date': ('django.db.models.fields.DateField', [], {}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'time_to_answer': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '3'})
        },
        'exmo2010.opennessexpression': {
            'Meta': {'object_name': 'OpennessExpression'},
            'code': ('django.db.models.fields.PositiveIntegerField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'-'", 'max_length': '255'})
        },
        'exmo2010.organization': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('name_ru', 'monitoring'), ('name_en', 'monitoring'), ('name_ka', 'monitoring'), ('name_az', 'monitoring'))", 'object_name': 'Organization'},
            'email': ('exmo2010.models.organization.EmailsField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inv_code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '6', 'blank': 'True'}),
            'inv_status': ('django.db.models.fields.CharField', [], {'default': "'NTS'", 'max_length': '3'}),
            'monitoring': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Monitoring']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'name_az': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name_en': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name_ka': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'name_ru': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'phone': ('exmo2010.models.organization.PhonesField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'exmo2010.parameter': {
            'Meta': {'ordering': "('code', 'name')", 'unique_together': "(('name_ru', 'monitoring'), ('name_en', 'monitoring'), ('name_ka', 'monitoring'), ('name_az', 'monitoring'), ('code', 'monitoring'))", 'object_name': 'Parameter'},
            'accessible': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'code': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('ckeditor.fields.RichTextField', [], {'blank': 'True'}),
            'description_az': ('ckeditor.fields.RichTextField', [], {'null': 'True', 'blank': 'True'}),
            'description_en': ('ckeditor.fields.RichTextField', [], {'null': 'True', 'blank': 'True'}),
            'description_ka': ('ckeditor.fields.RichTextField', [], {'null': 'True', 'blank': 'True'}),
            'description_ru': ('ckeditor.fields.RichTextField', [], {'null': 'True', 'blank': 'True'}),
            'document': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'exclude': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['exmo2010.Organization']", 'null': 'True', 'blank': 'True'}),
            'hypertext': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'monitoring': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Monitoring']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'name_az': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'name_en': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'name_ka': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'name_ru': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'npa': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'topical': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'weight': ('django.db.models.fields.IntegerField', [], {})
        },
        'exmo2010.qanswer': {
            'Meta': {'unique_together': "(('task', 'question'),)", 'object_name': 'QAnswer'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'numeral_answer': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.QQuestion']"}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Task']"}),
            'text_answer': ('django.db.models.fields.CharField', [], {'max_length': '300', 'blank': 'True'}),
            'variance_answer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.AnswerVariant']", 'null': 'True', 'blank': 'True'})
        },
        'exmo2010.qquestion': {
            'Meta': {'object_name': 'QQuestion'},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '600', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'qtype': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'questionnaire': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Questionnaire']"})
        },
        'exmo2010.questionnaire': {
            'Meta': {'object_name': 'Questionnaire'},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '600', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'monitoring': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Monitoring']", 'unique': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '300', 'blank': 'True'})
        },
        'exmo2010.score': {
            'Meta': {'ordering': "('task__user__username', 'task__organization__name', 'parameter__code')", 'unique_together': "(('task', 'parameter', 'revision'),)", 'object_name': 'Score'},
            'accessible': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'accessibleComment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'complete': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'completeComment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'document': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'documentComment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'edited': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'found': ('django.db.models.fields.IntegerField', [], {}),
            'foundComment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hypertext': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'hypertextComment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'imageComment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Parameter']"}),
            'revision': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Task']"}),
            'topical': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'topicalComment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'exmo2010.staticpage': {
            'Meta': {'object_name': 'StaticPage'},
            'content': ('ckeditor.fields.RichTextField', [], {'default': "''", 'blank': 'True'}),
            'content_az': ('ckeditor.fields.RichTextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'content_en': ('ckeditor.fields.RichTextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'content_ka': ('ckeditor.fields.RichTextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'content_ru': ('ckeditor.fields.RichTextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'description_az': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'description_en': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'description_ka': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'description_ru': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'primary_key': 'True'})
        },
        'exmo2010.task': {
            'Meta': {'ordering': "('organization__name', 'user__username')", 'unique_together': "(('user', 'organization'),)", 'object_name': 'Task'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Organization']"}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'exmo2010.taskhistory': {
            'Meta': {'ordering': "('timestamp',)", 'object_name': 'TaskHistory'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'task': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Task']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'exmo2010.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'digest_date_journal': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'notification_interval': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'notification_self': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'notification_thread': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'notification_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'organization': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['exmo2010.Organization']", 'null': 'True', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'max_length': '48', 'blank': 'True'}),
            'rt_comment_quantity': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rt_difference': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rt_final_openness': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rt_initial_openness': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rt_representatives': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'sex': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'subscribe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['exmo2010']
    symmetrical = True
