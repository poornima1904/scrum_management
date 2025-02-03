from django.contrib import admin
from django.urls import path, include
from scrum.views import TriggerNotificationView  # Import the notification view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('scrum.urls')),
    path('notifications/trigger/', TriggerNotificationView.as_view(), name='trigger-notification'),  # Notifications API
    path('', include('frontend.urls')),
]
