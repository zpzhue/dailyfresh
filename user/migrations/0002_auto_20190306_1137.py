# Generated by Django 2.1.5 on 2019-03-06 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='zip_code',
            field=models.CharField(blank=True, max_length=6, null=True, verbose_name='邮政编码'),
        ),
    ]