# Generated by Django 5.1.4 on 2025-01-10 18:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_delete_cards_delete_firebaseuser_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userdetails',
            name='id_token',
            field=models.CharField(default='N/A', max_length=1000, unique=True),
        ),
    ]
