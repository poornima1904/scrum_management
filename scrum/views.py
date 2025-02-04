from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate
from .models import User, Team, TeamMembership, Task
from .serializers import UserSerializer, TeamSerializer, TeamMembershipSerializer, TaskSerializer, UpdateTeamMemberRoleSerializer
from .permissions import IsScrumMaster, IsAdminOrAssignee, IsScrumMasterOrAdminTeam, SubteamPermission
from .utils.slack import SlackNotifier

# User Signup View
class UserListCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Allow signup for all users

    def perform_create(self, serializer):
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


# Assign Admin Role to Team Members
class AssignAdminView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsScrumMasterOrAdminTeam]

    def post(self, request):

        team_id = request.data.get("team")
        user_id = request.data.get("user")

        try:
            team = Team.objects.get(id=team_id)
            user = User.objects.get(id=user_id)
        except (Team.DoesNotExist, User.DoesNotExist):
            return Response({"error": "Invalid team or user"}, status=status.HTTP_400_BAD_REQUEST)

        membership, created = TeamMembership.objects.get_or_create(user=user, team=team)
        membership.role = 'Admin'
        membership.save()

        return Response({"message": f"User {user.username} is now an Admin of {team.name}"}, status=status.HTTP_200_OK)


# Team Membership List and Creation View
class TeamMembershipListCreateView(generics.ListCreateAPIView):
    queryset = TeamMembership.objects.all()
    serializer_class = TeamMembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsScrumMasterOrAdminTeam]


class TeamMembershipView(APIView):
    
    def patch(self, request, *args, **kwargs):
        serializer = UpdateTeamMemberRoleSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            # Extract user, team, and role data
            user = serializer.validated_data['user_id']
            team = serializer.validated_data['team_id']
            new_role = serializer.validated_data['role']
            
            # Update the role of the team member
            team_membership = TeamMembership.objects.get(user=user, team=team)
            team_membership.role = new_role
            team_membership.save()
            
            return Response({"message": f"User role updated to {new_role}"}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Task List and Creation View
class TaskListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsScrumMasterOrAdminTeam]

    def get(self, request):

        status = request.query_params.get("status", "To Do")

        tasks = Task.objects.filter(assigned_to=request.user, status=status).values_list('title', flat=True)
        return Response({"tasks": tasks}, status=200)

    def post(self, request):
        team = Team.objects.get(id=request.data['team'])
        # if not TeamMembership.objects.filter(team=team, user=request.user, role='Admin').exists():
        #     return Response({'error': 'Only Admins can create tasks'}, status=403)

        task = Task.objects.create(
            title=request.data['title'],
            team=team,
            created_by=request.user,
            assigned_to=User.objects.get(id=request.data['assigned_to_id']) #TODO: ADD assigned to validations
        )
        return Response(TaskSerializer(task).data, status=201)


# Task Detail View (Update Task Status)
class TaskDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrAssignee]

    def patch(self, request, pk):
        task = Task.objects.get(id=pk)
        self.check_object_permissions(request, task)

        task.status = request.data['status']
        task.save()
        return Response(TaskSerializer(task).data, status=200)

class TriggerNotificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get("user_id")
        message = request.data.get("message", "No message provided.")

        # Fetch user details (optional)
        try:
            user = User.objects.get(id=user_id)
            user_info = f"User: {user.username} (ID: {user.id})"
        except User.DoesNotExist:
            user_info = f"User with ID {user_id} does not exist."

        # Send notification to the app
        full_message = f"{message}\n{user_info}"
        print(f"Notification triggered: {full_message}")

        # Send notification to Slack
        slack_notifier = SlackNotifier()
        slack_response = slack_notifier.send_message(full_message)

        if slack_response:
            return Response({"message": "Notification triggered and sent to Slack successfully."}, status=200)
        return Response({"message": "Notification triggered but failed to send to Slack."}, status=500)


class TeamAPIView(APIView):

    def get(self, request, format=None):
        teams = Team.objects.all()  # Fetch all teams
        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = TeamSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            team = serializer.save()  # Save the new team
            return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)