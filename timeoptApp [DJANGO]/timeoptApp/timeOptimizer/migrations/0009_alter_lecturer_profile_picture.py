# Generated by Django 4.1.5 on 2023-04-12 15:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timeOptimizer', '0008_alter_lecturer_profile_picture'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lecturer',
            name='profile_picture',
            field=models.ImageField(default='default_pro_pic.jpg', upload_to='profile_pics'),
        ),
    ]
