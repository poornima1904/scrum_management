from celery import shared_task
from .models import Notification, User

@shared_task
def send_notification(user_id, message):
    try:
        user = User.objects.get(id=user_id)
        Notification.objects.create(user=user, message=message)
        return f'Notification sent to user {user.username}'
    except User.DoesNotExist:
        return f'User with ID {user_id} does not exist'
