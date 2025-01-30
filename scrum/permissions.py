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
        team_id = request.data.get("team")
        team = Team.objects.get(id=team_id)

        # Permission check: Allow Scrum Master or team Admin to add members
        if request.user.role == 'Scrum Master':
            return True
        # Permission check: Allow team Adminn or parent team admin to add members
        query_team = [team]
        parent_team = team.parent_team
        if parent_team is not None:
            query_team.append(parent_team)
        team_membership = TeamMembership.objects.filter(user=request.user, role='Admin', team__in=query_team)
        if len(team_membership) == len(query_team):
            return True
        return False


class IsAdminOrAssignee(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Only Admin or Assignee can update the task
        is_admin = TeamMembership.objects.filter(team=obj.team, user=request.user, role='Admin').exists()
        is_assignee = obj.assigned_to == request.user
        return is_admin or is_assignee
