from django.contrib.auth.models import AbstractUser
from django.db import models


# User Model
class User(AbstractUser):
    ROLE_CHOICES = (
        ('Scrum Master', 'Scrum Master'),
        ('Admin', 'Admin'),
        ('Member', 'Member'),
    )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)

    def save(self, *args, **kwargs):
        # Ensure only one Scrum Master exists
        if self.role == 'Scrum Master' and User.objects.filter(role='Scrum Master').exists():
            raise ValueError("Only one Scrum Master is allowed in the system.")
        super().save(*args, **kwargs)


# Team Model
class Team(models.Model):
    name = models.CharField(max_length=255, unique=True)
    parent_team = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_teams'
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_teams")
    members = models.ManyToManyField(User, through='TeamMembership')


# Team Membership Model
class TeamMembership(models.Model):
    ROLE_CHOICES = (
        ('Admin', 'Admin'),
        ('Member', 'Member'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)



# Task Model
class Task(models.Model):
    STATUS_CHOICES = (
        ('To Do', 'To Do'),
        ('In Progress', 'In Progress'),
        ('Complete', 'Complete'),
    )
    title = models.CharField(max_length=255)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tasks')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks')
    assigned_to = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='assigned_tasks', null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='To Do')

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
