# Generated by Django 4.1.13 on 2024-11-15 09:50

from django.db import migrations, models
import django.utils.timezone
import web.models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='object_id',
            field=models.CharField(default=web.models.generate_object_id, editable=False, max_length=24),
        ),
        migrations.AddField(
            model_name='person',
            name='reg_no',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='person',
            name='time',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterModelTable(
            name='person',
            table='DetectionDB',
        ),
    ]
