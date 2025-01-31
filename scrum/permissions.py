from rest_framework.permissions import BasePermission
from .models import TeamMembership, Team, User


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

        if request.user.role == 'Scrum Master':
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
