from rest_framework import serializers
from .models import TeamMembership, User, Team, Task


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)  # Ensure password is write-only

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']
        # read_only_fields = ['role']  # Role cannot be modified directly

    def create(self, validated_data):
        # Use the `set_password` method to hash the password
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user



class TeamSerializer(serializers.ModelSerializer):
    sub_teams = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'parent_team', 'created_by', 'sub_teams', 'members']
        read_only_fields = ['created_by']


class TeamMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMembership
        fields = ['id', 'user', 'team', 'role']

    # def create(self, validated_data):
    #     team = validated_data.get("team")
    #     user = validated_data.get("user")
    #     role = validated_data.get("role")

    #     # Permission check: Allow Scrum Master or team Admin to add members
    #     if self.request.user.role == 'Scrum Master':
    #         # Scrum Master can assign roles in any team
    #         pass
    #     elif self.request.user.role == 'Admin':
    #         if not TeamMembership.objects.filter(team=team, user=self.request.user, role='Admin').exists():
    #             raise PermissionError("You do not have permission to assign roles in this team.")
    #     else:
    #         raise PermissionError("Only Scrum Master or Admins can assign roles.")

    #     # Ensure the user is not already a member
    #     if TeamMembership.objects.filter(team=team, user=user).exists():
    #         raise ValueError("User is already a member of this team.")
        
    #     teamMembership = TeamMembership(team=team, user=user, role=role)
    #     teamMembership.save()
    #     return teamMembership


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'team', 'created_by', 'assigned_to', 'status']
