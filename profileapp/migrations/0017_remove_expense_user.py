# Generated by Django 5.0.7 on 2024-08-18 10:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profileapp', '0016_remove_expense_purpose'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='expense',
            name='user',
        ),
    ]
