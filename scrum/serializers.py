from django.db import IntegrityError, transaction
from rest_framework import serializers
from .models import TeamMembership, User, Team, Task
from .utils.constants import SCRUM_MASTER


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



class TeamSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=255)
    parent_team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all(), required=False, allow_null=True)
    created_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)

    # Custom validation for parent_team (only Scrum Master can create parent teams)
    def validate_parent_team(self, value):
        user = self.context['request'].user  # Get the logged-in user
        
        if value is None:
            # If no parent team, only Scrum Master can create parent team
            if user.role != 'Scrum Master':
                raise serializers.ValidationError("Only the Scrum Master can create parent teams.")
        
        else:
            # Check if user is admin of the parent team or any of its ancestors
            if not self.is_user_team_admin(user, value):
                raise serializers.ValidationError("You must be an admin of the parent team to create a sub-team.")

        return value

    def is_user_team_admin(self, user, team):
        # Check if user is an admin of the team
        try:
            membership = TeamMembership.objects.get(user=user, team=team)
            if membership.role == 'admin':
                return True
        except TeamMembership.DoesNotExist:
            return False

        # If the team has a parent team, recursively check if user is admin of parent team
        if team.parent_team:
            return self.is_user_team_admin(user, team.parent_team)

        return False

    def create(self, validated_data):
        members = validated_data.pop('members', [])
        user = self.context['request'].user  # Get the currently logged-in user
        validated_data['created_by'] = user

        try:
            # Start a transaction to ensure atomicity
            with transaction.atomic():
                # Create the team
                team = Team.objects.create(**validated_data)
                
                # Create TeamMembership for the created_by user with 'admin' role
                TeamMembership.objects.create(user=user, team=team, role="admin")
                
                # Create TeamMembership for each member
                for member in members:
                    TeamMembership.objects.create(user=member, team=team, role="member")
                
                # Commit the transaction
                return team
        except Exception as e:
            if 'scrum_team_name_key' in str(e):
                raise serializers.ValidationError({"name": "A team with this name already exists."})
            # If an error occurs, the transaction will be rolled back
            raise serializers.ValidationError(f"An error occurred while creating the team: {str(e)}")

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.parent_team = validated_data.get('parent_team', instance.parent_team)
        instance.created_by = validated_data.get('created_by', instance.created_by)
        instance.save()
        return instance


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


class UpdateTeamMemberRoleSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    team_id = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    role = serializers.ChoiceField(choices=TeamMembership.ROLE_CHOICES)

    def validate(self, data):
        # Check if the logged-in user is a scrum master
        user = self.context['request'].user
        team = data['team_id']
        if user.role != SCRUM_MASTER:
            raise serializers.ValidationError("Only Scrum Master can assign roles.")

        # Check if the user exists in the team
        try:
            team_membership = TeamMembership.objects.get(user=data['user_id'], team=team)
        except TeamMembership.DoesNotExist:
            raise serializers.ValidationError("User is not a member of this team.")
        
        # Ensure the user is not being assigned the same role as before
        if team_membership.role == data['role']:
            raise serializers.ValidationError("User already has this role.")
        
        return data