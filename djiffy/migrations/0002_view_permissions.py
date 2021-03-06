# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-10 17:56
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djiffy', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='canvas',
            options={'ordering': ['manifest', 'order'], 'permissions': (('view_manifest', 'Can view IIIF Canvas'),), 'verbose_name': 'IIIF Canvas', 'verbose_name_plural': 'IIIF Canvases'},
        ),
        migrations.AlterModelOptions(
            name='manifest',
            options={'permissions': (('view_canvas', 'Can view IIIF Manifest'),), 'verbose_name': 'IIIF Manifest'},
        ),
    ]
