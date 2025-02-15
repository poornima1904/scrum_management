from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate
from django.db.models import Q
from django.db import transaction
from .models import User, Team, TeamMembership, Task
from .serializers import (
    UserSerializer, TeamSerializer,
    TeamMembershipSerializer, TaskSerializer,
    UpdateTeamMemberRoleSerializer, AddUserToTeamSerializer
)
from .permissions import (
    IsScrumMaster, IsAdminOrAssignee, IsTeamAdminOrAssigneeOrReadOnly,
    IsScrumMasterOrAdminTeam, SubteamPermission
)
from .utils.slack import SlackNotifier
from .utils.constants import ADMIN
from rest_framework.exceptions import ValidationError

# User Signup View
class UserListCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Allow signup for all users

    def perform_create(self, serializer):
        email = serializer.validated_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError({"email": ["A user with this email already exists."]})
        
        is_first_user = not User.objects.exists()
        user = serializer.save()
        user.set_password(serializer.validated_data['password'])
        user.save()

        # If first user, assign Scrum Master role
        if is_first_user:
            user.role = 'Scrum Master'
            user.save()

        # Create Token for the user
        Token.objects.create(user=user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(id=response.data['id'])
            token = Token.objects.get(user=user)
            response.data['token'] = token.key
        return response


# Login View
class LoginView(ObtainAuthToken):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "token": token.key,
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


# Team List and Creation View
class TeamListCreateView(generics.ListCreateAPIView):
    queryset = Team.objects.filter(parent_team=None)  # Root teams only
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        team = serializer.save(created_by=self.request.user)
        TeamMembership.objects.create(user=self.request.user, team=team, role='Admin')



# Team Membership List and Creation View
class TeamMembershipListCreateView(generics.ListCreateAPIView):
    queryset = TeamMembership.objects.all()
    serializer_class = TeamMembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsScrumMasterOrAdminTeam]

class TeamMembershipView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = AddUserToTeamSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user_id']
            team = serializer.validated_data['team_id']
            role = serializer.validated_data['role']

            with transaction.atomic():  # Ensure team membership creation is transactional
                # Check if the user is already in the team
                if TeamMembership.objects.filter(user=user, team=team).exists():
                    return Response({"message": "User is already a member of the team."}, status=status.HTTP_400_BAD_REQUEST)
                
                # Create the team membership
                team_membership = TeamMembership.objects.create(user=user, team=team, role=role)

                # Trigger Slack notification
                slack_notifier = SlackNotifier()
                message = f"User {user.username} has been added to the team '{team.name}' with the role '{role}'."
                slack_response = slack_notifier.send_message(message)

                if slack_response:
                    notification_status = "Notification sent to Slack successfully."
                else:
                    notification_status = "Failed to send notification to Slack."

            return Response({
                "message": f"User {user.username} added to team {team.name} with role {role}.",
                "notification_status": notification_status
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, *args, **kwargs):
        serializer = UpdateTeamMemberRoleSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            # Extract user, team, and role data
            user = serializer.validated_data['user_id']
            team = serializer.validated_data['team_id']
            new_role = serializer.validated_data['role']

            with transaction.atomic():  # Ensure role update is transactional
                # Update the role of the team member
                team_membership = TeamMembership.objects.get(user=user, team=team)
                old_role = team_membership.role  # Store the old role for notification
                team_membership.role = new_role
                team_membership.save()

                # Trigger Slack notification
                slack_notifier = SlackNotifier()
                message = (
                    f"User {user.username}'s role in team '{team.name}' has been updated from '{old_role}' to '{new_role}'."
                )
                slack_response = slack_notifier.send_message(message)

                if slack_response:
                    notification_status = "Notification sent to Slack successfully."
                else:
                    notification_status = "Failed to send notification to Slack."

            return Response({
                "message": f"User {user.username}'s role updated to {new_role}.",
                "notification_status": notification_status
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Task List and Creation View
class TaskViewSet(viewsets.ModelViewSet):
    """
    API for managing tasks.
    - Team admins & parent team admins can assign/view tasks.
    - Assignee & team admins can update status.
    - Team members can view team tasks.
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeamAdminOrAssigneeOrReadOnly]

    def get_queryset(self):
        user = self.request.user

        # Get all teams where the user is an admin
        admin_team_ids = TeamMembership.objects.filter(user=user, role='Admin').values_list("team_id", flat=True)

        # Get all parent teams where the user is an admin (recursively)
        def get_parent_admin_teams(team_ids):
            parent_team_ids = Team.objects.filter(id__in=team_ids).values_list("parent_team_id", flat=True)
            parent_team_ids = [t for t in parent_team_ids if t is not None]  # Remove None values
            if not parent_team_ids:
                return set()
            return set(parent_team_ids) | get_parent_admin_teams(parent_team_ids)

        # Find all parent teams where the user is an admin
        parent_admin_teams = get_parent_admin_teams(admin_team_ids)

        # Combine direct admin teams + parent admin teams
        all_admin_teams = set(admin_team_ids) | parent_admin_teams

        # Return tasks belonging to those teams
        tasks = Task.objects.filter(Q(team_id__in=all_admin_teams) | Q(assigned_to=user))
        return tasks

    def perform_create(self, serializer):
        user = self.request.user
        task = serializer.save(created_by=user)
        task.save()

        # Send Slack Notification when a new task is created
        slack_notifier = SlackNotifier()
        message = (f":memo: *New Task Created*\n"
                   f"Title: {task.title}\n"
                   f"Team: {task.team.name}\n"
                   f"Assigned To: {task.assigned_to.username if task.assigned_to else 'Not Assigned'}\n"
                   f"Created By: {user.username}")
        slack_notifier.send_message(message)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_status = instance.status  # Store old status before update

        response = super().update(request, *args, **kwargs)

        # Check if the status has changed
        new_status = self.get_object().status
        if old_status != new_status:
            # Send Slack Notification when a task's status is updated
            slack_notifier = SlackNotifier()
            message = (f":bulb: *Task Status Updated*\n"
                       f"Title: {instance.title}\n"
                       f"Team: {instance.team.name}\n"
                       f"Updated By: {request.user.username}\n"
                       f"Old Status: {old_status} ➝ New Status: {new_status}")
            slack_notifier.send_message(message)

        return response


class TriggerNotificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        team_id = request.data.get("team_id")
        user_id = request.data.get("user_id")
        role = request.data.get("role", "Member")  # Default role is Member

        # Fetch team and user details
        try:
            team = Team.objects.get(id=team_id)
            user = User.objects.get(id=user_id)
        except Team.DoesNotExist:
            return Response({"error": f"Team with ID {team_id} does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": f"User with ID {user_id} does not exist."}, status=status.HTTP_400_BAD_REQUEST)

        # Add user to the team
        membership, created = TeamMembership.objects.get_or_create(user=user, team=team)
        if not created:
            return Response({"message": f"User {user.username} is already a member of the team {team.name}."}, status=status.HTTP_400_BAD_REQUEST)

        membership.role = role
        membership.save()

        # Prepare notification message
        full_message = (
            f"A new user has been added to the team:\n"
            f"Team: {team.name}\n"
            f"User: {user.username} (ID: {user.id})\n"
            f"Role: {role}"
        )
        print(f"Notification triggered: {full_message}")

        # Send notification to Slack
        slack_notifier = SlackNotifier()
        slack_response = slack_notifier.send_message(full_message)

        if slack_response:
            return Response({"message": "User added to the team and notification sent to Slack successfully."}, status=200)
        return Response({"message": "User added to the team but failed to send notification to Slack."}, status=500)

class TeamAPIView(APIView):

    def get(self, request, format=None):
        teams = Team.objects.all()  # Fetch all teams
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = TeamSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            user = request.user
            name = serializer.validated_data['name']
            parent_team = serializer.validated_data.get('parent_team', None)

            with transaction.atomic():  # Ensure team creation and membership assignment are transactional
                # Create the team
                team = Team.objects.create(name=name, parent_team=parent_team, created_by=user)

                # Assign the creator as the team admin
                TeamMembership.objects.create(user=user, team=team, role='admin')

                # Initialize Slack Notifier
                slack_notifier = SlackNotifier()

                # Generate notification message
                if parent_team:
                    message = f"A new sub-team '{team.name}' has been created under '{parent_team.name}' by {user.username}."
                else:
                    message = f"A new team '{team.name}' has been created by {user.username}."

                # Send the notification to Slack
                slack_response = slack_notifier.send_message(message)

                if slack_response:
                    notification_status = "Notification sent to Slack successfully."
                else:
                    notification_status = "Failed to send notification to Slack."

            return Response({
                "message": f"Team '{team.name}' created successfully.",
                "notification_status": notification_status
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class UserTeamsView(APIView):
    """
    API to get the list of teams the authenticated user is a part of.
    Only accessible by Scrum Masters or Team Admins.
    Supports fetching sub-teams if `include_subteams=true` is provided.
    """

    permission_classes = [IsScrumMasterOrAdminTeam]  # Apply custom permission

    def get(self, request, *args, **kwargs):
        user = request.user
        include_subteams = request.query_params.get('include_subteams', 'false').lower() == 'true'

        # Fetch teams where the user has a membership
        user_team_ids = TeamMembership.objects.filter(user=user).values_list('team_id', flat=True)
        user_teams = Team.objects.filter(id__in=user_team_ids)

        if include_subteams:
            all_teams = set()  
            for team in user_teams:
                all_teams.update(self.get_all_teams_with_subteams(team))
            user_teams = list(all_teams)

        serializer = TeamSerializer(user_teams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_all_teams_with_subteams(self, team):
        """
        Recursively fetch all sub-teams for a given team.
        """
        teams = [team]  # Include the given team
        for sub_team in team.sub_teams.all():
            teams.extend(self.get_all_teams_with_subteams(sub_team))
        return teams