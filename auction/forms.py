# auction/forms.py - SIMPLE VERSION WITH NO VALIDATIONS
from django import forms
from django.contrib.auth import get_user_model
from .models import Player, Team, AuctionSession

User = get_user_model()

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Confirm Password'
    )
    
    # Player-specific fields - ALL optional, NO validation
    player_type = forms.ChoiceField(
        choices=[('', 'Select Type'), ('student', 'Student'), ('faculty', 'Faculty')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_player_type'})
    )
    
    roll_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 0242CS221003'})
    )
    
    course = forms.ChoiceField(
        choices=[
            ('', 'Select Course'),
            ('btech', 'B.Tech'),
            ('polytechnic', 'Polytechnic'),
            ('iti', 'ITI')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_course'})
    )
    
    branch = forms.ChoiceField(
        choices=[
            ('', 'Select Branch'),
            ('cse', 'Computer Science Engineering'),
            ('me', 'Mechanical Engineering'),
            ('mining', 'Mining Engineering'),
            ('ee', 'Electrical Engineering'),
            ('ce', 'Civil Engineering')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_branch'})
    )
    
    year_of_study = forms.ChoiceField(
        choices=[
            ('', 'Select Year'),
            ('1', 'First Year'),
            ('2', 'Second Year'),
            ('3', 'Third Year'),
            ('4', 'Fourth Year')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_year_of_study'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'user_type', 'phone', 'college', 'profile_picture']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_user_type'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'college': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only basic fields are required
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
    
    def clean(self):
        """MINIMAL validation - only password matching"""
        cleaned_data = super().clean()
        
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        # Only check if passwords match
        if password and confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', "Passwords don't match!")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        
        # Save all player fields without validation
        user.player_type = self.cleaned_data.get('player_type') or None
        
        roll = self.cleaned_data.get('roll_number', '').strip()
        user.roll_number = roll.upper() if roll else None
        
        user.course = self.cleaned_data.get('course') or None
        user.branch = self.cleaned_data.get('branch') or None
        user.year_of_study = self.cleaned_data.get('year_of_study') or None
        
        if commit:
            user.save()
        return user


class PlayerRegistrationForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['category', 'batting_style', 'bowling_style', 'previous_team']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'batting_style': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Right-hand bat'}),
            'bowling_style': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Right-arm fast'}),
            'previous_team': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Previous team (if any)'}),
        }


class TeamCreationForm(forms.ModelForm):
    owner = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='team_owner'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    manager = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type='team_manager'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Team
        fields = ['name', 'owner', 'manager', 'logo', 'total_purse', 'max_players']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'total_purse': forms.NumberInput(attrs={'class': 'form-control', 'value': 10000}),
            'max_players': forms.NumberInput(attrs={'class': 'form-control', 'value': 16, 'min': 11, 'max': 25}),
        }
    
    def save(self, commit=True):
        team = super().save(commit=False)
        team.purse_remaining = team.total_purse
        if commit:
            team.save()
        return team


class AuctionSessionForm(forms.ModelForm):
    class Meta:
        model = AuctionSession
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., SEPL 2025 Auction'}),
        }
        


# Add these forms to auction/forms.py

from django.contrib.auth.forms import PasswordChangeForm

class UserProfileEditForm(forms.ModelForm):
    """Base profile edit form for all users"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'college', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'college': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }


class PlayerProfileEditForm(forms.ModelForm):
    """Extended profile edit for players - includes player-specific fields"""
    
    player_type = forms.ChoiceField(
        choices=[('', 'Select Type'), ('student', 'Student'), ('faculty', 'Faculty')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_player_type'})
    )
    
    roll_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 0242CS221003'})
    )
    
    course = forms.ChoiceField(
        choices=[
            ('', 'Select Course'),
            ('btech', 'B.Tech'),
            ('polytechnic', 'Polytechnic'),
            ('iti', 'ITI')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_course'})
    )
    
    branch = forms.ChoiceField(
        choices=[
            ('', 'Select Branch'),
            ('cse', 'Computer Science Engineering'),
            ('me', 'Mechanical Engineering'),
            ('mining', 'Mining Engineering'),
            ('ee', 'Electrical Engineering'),
            ('ce', 'Civil Engineering')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_branch'})
    )
    
    year_of_study = forms.ChoiceField(
        choices=[
            ('', 'Select Year'),
            ('1', 'First Year'),
            ('2', 'Second Year'),
            ('3', 'Third Year'),
            ('4', 'Fourth Year')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_year_of_study'})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'college', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'college': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill player-specific fields
        if self.instance:
            self.fields['player_type'].initial = self.instance.player_type
            self.fields['roll_number'].initial = self.instance.roll_number
            self.fields['course'].initial = self.instance.course
            self.fields['branch'].initial = self.instance.branch
            self.fields['year_of_study'].initial = self.instance.year_of_study
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Update player-specific fields
        user.player_type = self.cleaned_data.get('player_type') or None
        
        roll = self.cleaned_data.get('roll_number', '').strip()
        user.roll_number = roll.upper() if roll else None
        
        user.course = self.cleaned_data.get('course') or None
        user.branch = self.cleaned_data.get('branch') or None
        user.year_of_study = self.cleaned_data.get('year_of_study') or None
        
        if commit:
            user.save()
        return user


class PlayerDetailsEditForm(forms.ModelForm):
    """Edit cricket-specific player details"""
    class Meta:
        model = Player
        fields = ['category', 'batting_style', 'bowling_style', 'previous_team']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'batting_style': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Right-hand bat'}),
            'bowling_style': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Right-arm fast'}),
            'previous_team': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Previous team (if any)'}),
        }