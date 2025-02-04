from rest_framework.permissions import BasePermission
from .models import TeamMembership, Team, User
from .utils.constants import SCRUM_MASTER


class IsScrumMaster(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'Scrum Master'

class SubteamPermission(BasePermission):
    def has_permission(self, request, view):
        parent_team_id = request.data.get("parent_team_id")
        try:
            team = Team.objects.get(id=parent_team_id)
        except (Team.DoesNotExist):
            return False
        if TeamMembership.objects.get(user=request.user, team=team):
            return True
        return False
    

class IsScrumMasterOrAdminTeam(BasePermission):

    def has_permission(self, request, view):

        if request.method == 'GET':
              return True

        if request.user.role == SCRUM_MASTER:
            return True

        if request.method == 'POST':
            team_id = request.data.get("team")
            team = Team.objects.get(id=team_id) #TODO: Hnadle error here
            if TeamMembership.objects.filter(user=request.user, role='Admin', team=team):
                return True
        return False


class IsAdminOrAssignee(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Only Admin or Assignee can update the task
        is_admin = TeamMembership.objects.filter(team=obj.team, user=request.user, role='Admin').exists()
        is_assignee = obj.assigned_to == request.user
        return is_admin or is_assignee

class IsTeamAdminOrAssigneeOrReadOnly(BasePermission):
    """
    - Admins (team + parent team admins) can assign/view tasks.
    - Admins & Assignees can update task status.
    - Team members can view tasks.
    """

    def is_admin_or_parent_admin(self, team, user):
        # Check if the user is an admin of the current team
        team_membership = TeamMembership.objects.filter(team=team, user=user).first()
        if team_membership and team_membership.role == 'admin':
            return True

        # If no admin role is found, check if there's a parent team and recursively check the parent team
        parent_team = team.parent_team
        if parent_team:
            return self.is_admin_or_parent_admin(parent_team, user)

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role == SCRUM_MASTER:
            return True

        # Allow read-only access for team members
        if request.method in ['GET']:
            return obj.team.members.filter(id=user.id).exists()

        # Assignee can update task status
        if request.method in ['PATCH', 'PUT']:
            if obj.assigned_to == user:
                return True

            if self.is_admin_or_parent_admin(obj.team, user):
                return True

        return False