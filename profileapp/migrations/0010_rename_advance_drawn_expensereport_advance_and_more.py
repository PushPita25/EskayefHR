# Generated by Django 5.0.7 on 2024-08-13 05:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profileapp', '0009_expensereport'),
    ]

    operations = [
        migrations.RenameField(
            model_name='expensereport',
            old_name='advance_drawn',
            new_name='advance',
        ),
        migrations.RenameField(
            model_name='expensereport',
            old_name='id_number',
            new_name='id_no',
        ),
    ]
