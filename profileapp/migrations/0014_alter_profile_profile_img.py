# Generated by Django 5.0.7 on 2024-08-17 15:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profileapp', '0013_expense'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='profile_img',
            field=models.ImageField(blank=True, default='media/profile.webp', null=True, upload_to='media'),
        ),
    ]
