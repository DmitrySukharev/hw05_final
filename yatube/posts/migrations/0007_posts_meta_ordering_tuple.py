# Generated by Django 2.2.6 on 2022-06-05 14:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0006_posts_meta_ordering'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='post',
            options={'ordering': ('-pub_date',)},
        ),
    ]
