# Generated by Django 5.1.6 on 2025-03-17 04:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hoadeptrai', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='stock_quantity',
        ),
        migrations.AddField(
            model_name='product',
            name='status',
            field=models.BooleanField(default=True),
        ),
    ]
