from django.shortcuts import render
from django.views.generic import TemplateView
class HomeView(TemplateView):
    """
    This view renders the home page.
    It displays the title and the navigation bar.
    """
    template_name = "base.html"


class DashboardView(TemplateView):
    """
    This view renders the dashboard page.
    It includes options for managing teams and tasks.
    """
    template_name = "dashboard.html"


class LoginView(TemplateView):
    """
    This view renders the login page.
    """
    template_name = "login.html"


class SignupView(TemplateView):
    """
    This view renders the signup page.
    """
    template_name = "signup.html"


class ManageTeamsView(TemplateView):
    """
    This view renders the page to manage teams.
    """
    template_name = "manage_teams.html"


class ManageTasksView(TemplateView):
    """
    This view renders the page to manage tasks.
    """
    template_name = "manage_tasks.html"
