# Generated by Django 3.2.3 on 2021-05-31 04:11

from django.db import migrations
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0003_alter_parameter_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parameter',
            name='description',
            field=tinymce.models.HTMLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='refactoring',
            name='description',
            field=tinymce.models.HTMLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='refactoring',
            name='input_example',
            field=tinymce.models.HTMLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='refactoring',
            name='output_example',
            field=tinymce.models.HTMLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='refactoring',
            name='post_conditions',
            field=tinymce.models.HTMLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='refactoring',
            name='pre_conditions',
            field=tinymce.models.HTMLField(blank=True, null=True),
        ),
    ]