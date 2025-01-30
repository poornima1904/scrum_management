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

    # def validate(self, data):
    #     team = data['team']
    #     user = data['user']
    #     if TeamMembership.objects.filter(team=team, user=user).exists():
    #         raise serializers.ValidationError("User is already a member of this team.")
    #     return data


class TeamMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMembership
        fields = ['id', 'user', 'team', 'role']

    def validate(self, data):
        team = data['team']
        user = data['user']
        if TeamMembership.objects.filter(team=team, user=user).exists():
            raise serializers.ValidationError("User is already a member of this team.")
        return data


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'team', 'created_by', 'assigned_to', 'status']
