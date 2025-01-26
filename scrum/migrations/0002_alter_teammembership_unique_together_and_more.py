# Generated by Django 5.1.5 on 2025-01-24 09:20

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('scrum', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='teammembership',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='team',
            name='created_at',
        ),
        migrations.AddField(
            model_name='team',
            name='members',
            field=models.ManyToManyField(through='scrum.TeamMembership', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='team',
            name='parent_team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sub_teams', to='scrum.team'),
        ),
        migrations.AlterField(
            model_name='teammembership',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='scrum.team'),
        ),
        migrations.AlterField(
            model_name='teammembership',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups'),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(blank=True, choices=[('Scrum Master', 'Scrum Master'), ('Admin', 'Admin'), ('Member', 'Member')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions'),
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('To Do', 'To Do'), ('In Progress', 'In Progress'), ('Complete', 'Complete')], default='To Do', max_length=20)),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assigned_tasks', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_tasks', to=settings.AUTH_USER_MODEL)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='scrum.team')),
            ],
        ),
    ]
