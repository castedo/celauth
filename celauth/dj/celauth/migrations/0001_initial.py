# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'OpenIDNonce'
        db.create_table(u'celauth_openidnonce', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('server_url', self.gf('django.db.models.fields.URLField')(max_length=255)),
            ('timestamp', self.gf('django.db.models.fields.IntegerField')()),
            ('salt', self.gf('django.db.models.fields.CharField')(max_length=40)),
        ))
        db.send_create_signal(u'celauth', ['OpenIDNonce'])

        # Adding model 'OpenIDAssociation'
        db.create_table(u'celauth_openidassociation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('server_url', self.gf('django.db.models.fields.URLField')(max_length=200, db_index=True)),
            ('handle', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('secret', self.gf('django.db.models.fields.TextField')(max_length=255)),
            ('issued', self.gf('django.db.models.fields.IntegerField')()),
            ('lifetime', self.gf('django.db.models.fields.IntegerField')()),
            ('assoc_type', self.gf('django.db.models.fields.TextField')(max_length=64)),
        ))
        db.send_create_signal(u'celauth', ['OpenIDAssociation'])

        # Adding model 'EmailAddress'
        db.create_table(u'celauth_emailaddress', (
            ('address', self.gf('django.db.models.fields.EmailField')(max_length=75, primary_key=True)),
            ('account', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True, null=True, blank=True)),
        ))
        db.send_create_signal(u'celauth', ['EmailAddress'])

        # Adding model 'OpenID'
        db.create_table(u'celauth_openid', (
            ('claimed_id', self.gf('django.db.models.fields.URLField')(max_length=255, primary_key=True)),
            ('display_id', self.gf('django.db.models.fields.URLField')(max_length=255)),
            ('account', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True, null=True, blank=True)),
            ('email', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['celauth.EmailAddress'], null=True, blank=True)),
            ('confirmed', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'celauth', ['OpenID'])

        # Adding model 'ConfirmationCode'
        db.create_table(u'celauth_confirmationcode', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['celauth.EmailAddress'])),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('expiration', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal(u'celauth', ['ConfirmationCode'])


    def backwards(self, orm):
        # Deleting model 'OpenIDNonce'
        db.delete_table(u'celauth_openidnonce')

        # Deleting model 'OpenIDAssociation'
        db.delete_table(u'celauth_openidassociation')

        # Deleting model 'EmailAddress'
        db.delete_table(u'celauth_emailaddress')

        # Deleting model 'OpenID'
        db.delete_table(u'celauth_openid')

        # Deleting model 'ConfirmationCode'
        db.delete_table(u'celauth_confirmationcode')


    models = {
        u'celauth.confirmationcode': {
            'Meta': {'object_name': 'ConfirmationCode'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['celauth.EmailAddress']"}),
            'expiration': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'celauth.emailaddress': {
            'Meta': {'object_name': 'EmailAddress'},
            'account': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'address': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'primary_key': 'True'})
        },
        u'celauth.openid': {
            'Meta': {'object_name': 'OpenID'},
            'account': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'claimed_id': ('django.db.models.fields.URLField', [], {'max_length': '255', 'primary_key': 'True'}),
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_id': ('django.db.models.fields.URLField', [], {'max_length': '255'}),
            'email': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['celauth.EmailAddress']", 'null': 'True', 'blank': 'True'})
        },
        u'celauth.openidassociation': {
            'Meta': {'object_name': 'OpenIDAssociation'},
            'assoc_type': ('django.db.models.fields.TextField', [], {'max_length': '64'}),
            'handle': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issued': ('django.db.models.fields.IntegerField', [], {}),
            'lifetime': ('django.db.models.fields.IntegerField', [], {}),
            'secret': ('django.db.models.fields.TextField', [], {'max_length': '255'}),
            'server_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'db_index': 'True'})
        },
        u'celauth.openidnonce': {
            'Meta': {'object_name': 'OpenIDNonce'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'salt': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'server_url': ('django.db.models.fields.URLField', [], {'max_length': '255'}),
            'timestamp': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['celauth']