from django.urls import path
from .views import (
    UserListCreateView,
    LoginView,
    TeamListCreateView,
    AssignAdminView,
    TeamMembershipListCreateView,
    TaskListCreateView,
    TaskDetailView,
    TriggerNotificationView,
    TeamMembershipView,
    TeamAPIView
)

urlpatterns = [
    path('users/', UserListCreateView.as_view(), name='user-list-create'),  # Signup Endpoint
    path('login/', LoginView.as_view(), name='login'),  # Login Endpoint
    path('teams/', TeamAPIView.as_view(), name='team-list-create'),  # Create or List Teams
    path('team-membership/', TeamMembershipView.as_view(), name='team-membership-list-create'),  # Manage Memberships
    path('assign-admin/', AssignAdminView.as_view(), name='assign-admin'),  # Assign Admin Role
    path('tasks/', TaskListCreateView.as_view(), name='task-list-create'),  # Create Tasks
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),  # Update Task Status
    path('notifications/trigger/', TriggerNotificationView.as_view(), name='trigger-notification'),

]
