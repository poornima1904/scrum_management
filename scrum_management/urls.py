from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView, TokenBlacklistView
from scrum.views import TriggerNotificationView  # Import the notification view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('scrum.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Login
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Refresh Token
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),  # Logout
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('notifications/trigger/', TriggerNotificationView.as_view(), name='trigger-notification'),  # Notifications API
    path('', include('frontend.urls')),
]
