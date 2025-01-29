from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate
from .models import User, Team, TeamMembership, Task
from .serializers import UserSerializer, TeamSerializer, TeamMembershipSerializer, TaskSerializer
from .permissions import IsScrumMaster, IsScrumMasterOrAdmin, IsAdminOrAssignee, IsScrumMasterOrAdminTeam
from .utils.slack import SlackNotifier

# User Signup View
class UserListCreateView(generics.ListCreateAPIView):
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
    permission_classes = [permissions.IsAuthenticated, IsScrumMaster]

    def perform_create(self, serializer):
        team = serializer.save(created_by=self.request.user)
        TeamMembership.objects.create(user=self.request.user, team=team, role='Admin')


# Assign Admin Role to Team Members
class AssignAdminView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsScrumMasterOrAdminTeam]

    def post(self, request):
        team_id = request.data.get("team_id")
        user_id = request.data.get("user_id")

        try:
            team = Team.objects.get(id=team_id)
            user = User.objects.get(id=user_id)
        except (Team.DoesNotExist, User.DoesNotExist):
            return Response({"error": "Invalid team or user"}, status=status.HTTP_400_BAD_REQUEST)

        membership, created = TeamMembership.objects.get_or_create(user=user, team=team)
        membership.role = 'Admin'
        user.role = 'Admin'
        user.save()
        membership.save()

        return Response({"message": f"User {user.username} is now an Admin of {team.name}"}, status=status.HTTP_200_OK)


# Sub-Team Creation View
class SubTeamCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsScrumMasterOrAdmin]

    def post(self, request):
        parent_team = Team.objects.get(id=request.data['parent_team_id'])
        if not TeamMembership.objects.filter(team=parent_team, user=request.user, role='Admin').exists():
            return Response({'error': 'Only Admins can create sub-teams'}, status=403)

        sub_team = Team.objects.create(
            name=request.data['name'],
            parent_team=parent_team,
            created_by=request.user
        )
        TeamMembership.objects.create(user=request.user, team=sub_team, role='Admin')
        return Response(TeamSerializer(sub_team).data, status=201)


# Team Membership List and Creation View
class TeamMembershipListCreateView(generics.ListCreateAPIView):
    queryset = TeamMembership.objects.all()
    serializer_class = TeamMembershipSerializer
    permission_classes = [permissions.IsAuthenticated, IsScrumMasterOrAdminTeam]


# Task List and Creation View
class TaskListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsScrumMasterOrAdmin]

    def post(self, request):
        team = Team.objects.get(id=request.data['team_id'])
        if not TeamMembership.objects.filter(team=team, user=request.user, role='Admin').exists():
            return Response({'error': 'Only Admins can create tasks'}, status=403)

        task = Task.objects.create(
            title=request.data['title'],
            team=team,
            created_by=request.user,
            assigned_to=User.objects.get(id=request.data['assigned_to_id'])
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
