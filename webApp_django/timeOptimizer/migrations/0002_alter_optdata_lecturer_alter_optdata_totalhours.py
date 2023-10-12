# Generated by Django 4.1.5 on 2023-03-30 01:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('timeOptimizer', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='optdata',
            name='lecturer',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='timeOptimizer.lecturer'),
        ),
        migrations.AlterField(
            model_name='optdata',
            name='totalHours',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
