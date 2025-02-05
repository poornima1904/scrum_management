from django.db import IntegrityError, transaction
from rest_framework import serializers
from .models import TeamMembership, User, Team, Task
from .utils.constants import SCRUM_MASTER, ADMIN


def is_team_admin_or_scrum_master(user, team):
    """
    Check if the user is a team admin for the given team (or any of its parent teams) 
    or if the user is a Scrum Master.
    """
    if user.role == SCRUM_MASTER:  # Scrum Master has full access
        return True

    try:
        # Check if the user is an admin for the current team
        membership = TeamMembership.objects.get(user=user, team=team)
        if membership.role == ADMIN:
            return True

        # Recursively check if the user is an admin of any parent teams
        if team.parent_team:
            return is_team_admin_or_scrum_master(user, team.parent_team)

        return False
    except TeamMembership.DoesNotExist:
        return False


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)  # Ensure password is write-only

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']
        # read_only_fields = ['role']  # Role cannot be modified directly
    
    def validate_email(self, value):
        """ Ensure email is unique """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

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
    def validate(self, data):
        user = self.context['request'].user
        parent_team = data.get('parent_team', None)

        # Only Scrum Master can create parent teams
        if parent_team is None and user.role != SCRUM_MASTER:
            raise serializers.ValidationError("Only Scrum Master can create parent teams.")

        # Check if the user is a valid Team Admin for sub-team creation
        if parent_team and not is_team_admin_or_scrum_master(user, parent_team):
            raise serializers.ValidationError("Only Team Admins or Scrum Masters can create sub-teams.")

        # Ensure team name is unique
        if Team.objects.filter(name=data['name']).exists():
            raise serializers.ValidationError("A team with this name already exists.")

        return data

    def is_user_team_admin(self, user, team):
        # Check if user is an admin of the team
        try:
            membership = TeamMembership.objects.get(user=user, team=team)
            if membership.role == ADMIN:
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
        read_only_fields = ['id', 'created_by']  # Prevent users from modifying these fields

    def validate_team(self, value):

        if not value:
            raise serializers.ValidationError("Team id is required")
        # Validate that the team exists
        if not Team.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Invalid team ID.")
        return value

    def validate_assigned_to(self, value):
        # Validate that the assigned user exists
        if value and not User.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Assigned user does not exist.")
        return value

    def validate(self, attrs):
        assigned_to = attrs.get('assigned_to')
        assigned_team_task_id =  attrs.get('team').id
        user_teams = TeamMembership.objects.filter(user_id=assigned_to).values_list("team_id", flat=True)
        # Custom validation for any other business logic
        if assigned_to and attrs.get('created_by') ==assigned_to:
            raise serializers.ValidationError("Assigned user cannot be the same as the creator.")
         # ensure the user is from the same team
        if assigned_team_task_id not in user_teams:
            raise serializers.ValidationError("Cannot assign task of some other team")
        return attrs


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


class AddUserToTeamSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    team_id = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    role = serializers.ChoiceField(choices=TeamMembership.ROLE_CHOICES, default='member')  # Default role is "member"
    
    def validate(self, data):
        request_user = self.context['request'].user
        target_team = data['team_id']

        # Allow Scrum Masters to add users to any team
        if request_user.role != SCRUM_MASTER and not is_team_admin_or_scrum_master(request_user, target_team):
            raise serializers.ValidationError("Only Scrum Master or Team Admin can add users to a team.")

        # Ensure that the user being added is not already a member of the team
        if TeamMembership.objects.filter(user=data['user_id'], team=target_team).exists():
            raise serializers.ValidationError("User is already a member of this team.")

        return data
