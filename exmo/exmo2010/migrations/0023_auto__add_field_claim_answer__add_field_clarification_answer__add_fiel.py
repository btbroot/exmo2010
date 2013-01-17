# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from exmo2010.models import UserProfile


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Cоздание бэкапа (таблицы "backup_exmo2010_claim" - копии "exmo2010_claim") и копирование в нее
        # претензий, созданных Аналитиками (ранее являвшиеся ответами на претензии от Экспертов).
        # Удаление этих претензий из оригинальной таблицы.
        # В обеих таблицах id c auto_increment'ом. Поэтому порядок расположения в таблице не важен.
        sql_claims_selection = 'FROM exmo2010_claim WHERE creator_id IN (SELECT user_id FROM \
        auth_user_groups WHERE group_id=(SELECT id FROM auth_group \
        WHERE name="%s")) AND creator_id NOT IN \
        (SELECT user_id FROM auth_user_groups WHERE \
        group_id=(SELECT id FROM auth_group WHERE name="%s")) \
        AND creator_id NOT IN (SELECT user_id FROM auth_user_groups \
        WHERE group_id=(SELECT id FROM auth_group \
        WHERE name="%s"));' % (UserProfile.expertB_group,
                               UserProfile.expertA_group,
                               UserProfile.expertB_manager_group)

        db.execute('CREATE TABLE IF NOT EXISTS backup_exmo2010_claim LIKE exmo2010_claim;')
        db.execute('INSERT INTO backup_exmo2010_claim SELECT * ' + sql_claims_selection)
        db.execute('DELETE ' + sql_claims_selection)

        # Adding field 'Claim.answer'
        db.add_column('exmo2010_claim', 'answer',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Clarification.answer'
        db.add_column('exmo2010_clarification', 'answer',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Clarification.close_user'
        db.add_column('exmo2010_clarification', 'close_user',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='clarification_close_user', null=True, to=orm['auth.User']),
                      keep_default=False)

    # После отката миграции, откатываться придется и
    # до коммита, где поля answer не используются.
    def backwards(self, orm):
        # Deleting field 'Claim.answer'
        db.delete_column('exmo2010_claim', 'answer')

        # Deleting field 'Clarification.answer'
        db.delete_column('exmo2010_clarification', 'answer')

        # Deleting field 'Clarification.close_user'
        db.delete_column('exmo2010_clarification', 'close_user_id')

        # Восстановление из бэкапа (таблицы "backup_exmo2010_claim" - копии "exmo2010_claim")
        # претензий, созданных аналитиками. Удаление таблицы с бекапом.
        db.execute('INSERT INTO exmo2010_claim SELECT * FROM backup_exmo2010_claim;')
        db.execute('DROP TABLE backup_exmo2010_claim;')


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
        'exmo2010.monitoring': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Monitoring'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'-'", 'max_length': '255'}),
            'openness_expression': ('django.db.models.fields.related.ForeignKey', [], {'default': '8', 'to': "orm['exmo2010.OpennessExpression']"}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'time_to_answer': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '3'})
        },
        'exmo2010.monitoringinteractactivity': {
            'Meta': {'unique_together': "(('user', 'monitoring'),)", 'object_name': 'MonitoringInteractActivity'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'monitoring': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Monitoring']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'exmo2010.monitoringstatus': {
            'Meta': {'ordering': "('status', '-start')", 'unique_together': "(('status', 'monitoring'),)", 'object_name': 'MonitoringStatus'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'monitoring': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Monitoring']"}),
            'start': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'exmo2010.opennessexpression': {
            'Meta': {'object_name': 'OpennessExpression'},
            'code': ('django.db.models.fields.PositiveIntegerField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'-'", 'max_length': '255'})
        },
        'exmo2010.organization': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('name', 'monitoring'),)", 'object_name': 'Organization'},
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inv_code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '6', 'blank': 'True'}),
            'keywords': ('exmo2010.fields.TagField', [], {'null': 'True'}),
            'monitoring': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Monitoring']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'exmo2010.parameter': {
            'Meta': {'ordering': "('code', 'name')", 'unique_together': "(('code', 'monitoring'), ('name', 'monitoring'))", 'object_name': 'Parameter'},
            'accessible': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'code': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'document': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'exclude': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['exmo2010.Organization']", 'null': 'True', 'blank': 'True'}),
            'hypertext': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'keywords': ('exmo2010.fields.TagField', [], {}),
            'monitoring': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Monitoring']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
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
        'exmo2010.task': {
            'Meta': {'ordering': "('organization__name', 'user__username')", 'unique_together': "(('user', 'organization'),)", 'object_name': 'Task'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'openness_first': ('django.db.models.fields.FloatField', [], {'default': '-1'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['exmo2010.Organization']"}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'exmo2010.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['exmo2010.Organization']", 'null': 'True', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'max_length': '48', 'blank': 'True'}),
            'preference': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sex': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'subscribe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['exmo2010']