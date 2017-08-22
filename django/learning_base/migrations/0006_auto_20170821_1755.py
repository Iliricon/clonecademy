# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-08-21 17:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning_base', '0005_auto_20170816_0942'),
    ]

    operations = [
        migrations.RenameField(
            model_name='question',
            old_name='body',
            new_name='text',
        ),
        migrations.AddField(
            model_name='course',
            name='description',
            field=models.CharField(blank=True, max_length=144, null=True),
        ),
        migrations.AddField(
            model_name='module',
            name='description',
            field=models.CharField(blank=True, max_length=144, null=True),
        ),
        migrations.AddField(
            model_name='question',
            name='question',
            field=models.TextField(default='the question', help_text='This field can contain markdown syntax', verbose_name='Question'),
            preserve_default=False,
        ),
    ]
