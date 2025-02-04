from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    UserListCreateView,
    LoginView,
    TaskViewSet,
    TriggerNotificationView,
    TeamMembershipView,
    TeamAPIView,
    UserTeamsView
)
router = DefaultRouter()
router.register(r'task', TaskViewSet, basename='task')

urlpatterns = [
    path('users/', UserListCreateView.as_view(), name='user-list-create'),  # Signup Endpoint
    path('login/', LoginView.as_view(), name='login'),  # Login Endpoint
    path('teams/', TeamAPIView.as_view(), name='team-list-create'),  # Create or List Teams
    path('team-membership/', TeamMembershipView.as_view(), name='team-membership-list-create'),  # Manage Memberships
    path('user/teams', UserTeamsView.as_view(), name='team-membership-list-create'),  # Manage Memberships
    # path('task/', TaskViewSet.as_view(), name='task-list-create'),  # Create Tasks
    # path('task/<int:pk>/', TaskViewSet.as_view(), name='task-detail'),  # Update Task Status
    path('', include(router.urls)),
    path('notifications/trigger/', TriggerNotificationView.as_view(), name='trigger-notification'),
]
