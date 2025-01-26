from rest_framework.permissions import BasePermission
from .models import TeamMembership, Team, User


class IsScrumMaster(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'Scrum Master'


class IsScrumMasterOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ['Scrum Master', 'Admin']
    

class IsScrumMasterOrAdminTeam(BasePermission):

    def has_permission(self, request, view):
        team_id = request.data.get("team")
        user_id = request.data.get("user")
        # role = request.data.get("role")

        team = Team.objects.get(id=team_id)
        user = User.objects.get(id=user_id)

        # Permission check: Allow Scrum Master or team Admin to add members
        if request.user.role == 'Scrum Master':
            # Scrum Master can assign roles in any team
            pass
        elif request.user.role == 'Admin':
            if not TeamMembership.objects.filter(team=team, user=request.user, role='Admin').exists():
                return False
                raise PermissionError("You do not have permission to assign roles in this team.")
        else:
            return False
            raise PermissionError("Only Scrum Master or Admins can assign roles.")

        # Ensure the user is not already a member
        if TeamMembership.objects.filter(team=team, user=user).exists():
            raise ValueError("User is already a member of this team.")
        return True

    


class IsAdminOrAssignee(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Only Admin or Assignee can update the task
        is_admin = TeamMembership.objects.filter(team=obj.team, user=request.user, role='Admin').exists()
        is_assignee = obj.assigned_to == request.user
        return is_admin or is_assignee
