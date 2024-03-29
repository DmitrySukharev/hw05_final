# Generated by Django 2.2.16 on 2022-06-17 11:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0010_follow'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='follow',
            constraint=models.UniqueConstraint(fields=('user', 'author'), name='unique_user_author_pair'),
        ),
    ]
