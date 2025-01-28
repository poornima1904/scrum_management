from django.urls import path
from .views import (
    UserListCreateView,
    LoginView,
    TeamListCreateView,
    AssignAdminView,
    SubTeamCreateView,
    TeamMembershipListCreateView,
    TaskListCreateView,
    TaskDetailView,
    TriggerNotificationView
)

urlpatterns = [
    path('users/', UserListCreateView.as_view(), name='user-list-create'),  # Signup Endpoint
    path('login/', LoginView.as_view(), name='login'),  # Login Endpoint
    path('teams/', TeamListCreateView.as_view(), name='team-list-create'),  # Create or List Teams
    path('sub-teams/', SubTeamCreateView.as_view(), name='sub-team-create'),  # Create Sub-Teams
    path('team-memberships/', TeamMembershipListCreateView.as_view(), name='team-membership-list-create'),  # Manage Memberships
    path('assign-admin/', AssignAdminView.as_view(), name='assign-admin'),  # Assign Admin Role
    path('tasks/', TaskListCreateView.as_view(), name='task-list-create'),  # Create Tasks
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),  # Update Task Status
    path('notifications/trigger/', TriggerNotificationView.as_view(), name='trigger-notification'),

]
