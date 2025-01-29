from django.urls import path
from frontend import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('dashboard/manage-teams/', views.ManageTeamsView.as_view(), name='manage_teams'),
    path('dashboard/manage-tasks/', views.ManageTasksView.as_view(), name='manage_tasks'),
]
