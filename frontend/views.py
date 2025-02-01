from django.views import View
import requests
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from frontend.forms import SignupForm, LoginForm
from scrum.models import User
from scrum.serializers import UserSerializer
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.contrib.auth import logout

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


class LoginView(View):
    """
    This view handles GET and POST requests for the login page.
    """

    template_name = "login.html"

    def get(self, request, *args, **kwargs):
        form = LoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            # Authenticate the user
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)

                # Generate or fetch an authentication token for the user
                token, created = Token.objects.get_or_create(user=user)

                # Store the token in the session
                request.session["auth_token"] = token.key

                # Redirect to dashboard after login
                return redirect("dashboard")
            else:
                return render(request, self.template_name, {"form": form, "errors": "Invalid credentials"})
        return render(request, self.template_name, {"form": form, "errors": form.errors})


class LogoutView(View):
    """
    This view logs out the user and redirects them to the login page.
    """

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("login")
class SignupView(View):
    """
    This view handles GET and POST requests for the signup page.
    """

    template_name = "signup.html"

    def get(self, request, *args, **kwargs):
        form = SignupForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = SignupForm(request.POST)
        if form.is_valid():
            # Extract form data
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # Validate and save using the serializer
            serializer = UserSerializer(data={
                "username": username,
                "email": email,
                "password": password,
            })
            if serializer.is_valid():
                user = serializer.save()
                user.set_password(password)
                user.save()

                # Create token for the new user
                Token.objects.create(user=user)

                # Redirect to login page
                return redirect("login")
            else:
                # Handle serializer validation errors
                return render(request, self.template_name, {"form": form, "errors": serializer.errors})
        else:
            # Handle form validation errors
            return render(request, self.template_name, {"form": form, "errors": form.errors})


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

class ManageTeamMembershipsView(TemplateView):
    template_name = "manage_team_memberships.html"
