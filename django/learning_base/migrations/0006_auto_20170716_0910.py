# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-07-16 09:10
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning_base', '0005_auto_20170708_1155'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='modrequest',
            name='user',
        ),
        migrations.AddField(
            model_name='profile',
            name='last_modrequest',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.DeleteModel(
            name='ModRequest',
        ),
    ]