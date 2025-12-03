from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from cloudinary.models import CloudinaryField
class User(AbstractUser):
    USER_TYPES = (
        ('player', 'Player'),
        ('team_owner', 'Team Owner'),
        ('team_manager', 'Team Manager'),
        ('umpire', 'Umpire'),
        # ('auctioneer', 'Auctioneer'),
        # ('admin', 'Administrator'),
    )
    
    PLAYER_TYPES = (
        ('student', 'Student'),
        ('faculty', 'Faculty'),
    )
    
    COURSE_CHOICES = (
        ('btech', 'B.Tech'),
        ('polytechnic', 'Polytechnic'),
        ('iti', 'ITI'),
    )
    
    BRANCH_CHOICES = (
        ('cse', 'Computer Science Engineering'),
        ('me', 'Mechanical Engineering'),
        ('mining', 'Mining Engineering'),
        ('ee', 'Electrical Engineering'),
        ('ce', 'Civil Engineering'),
    )
    
    YEAR_CHOICES = (
        ('1', 'First Year'),
        ('2', 'Second Year'),
        ('3', 'Third Year'),
        ('4', 'Fourth Year'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    phone = models.CharField(max_length=10, blank=True)
    college = models.CharField(max_length=200, blank=True)
    profile_picture = CloudinaryField('image', folder='sepl/profile/', blank=True, null=True)

    
    # Player specific fields - ALL OPTIONAL, NO VALIDATION
    player_type = models.CharField(max_length=10, choices=PLAYER_TYPES, blank=True, null=True)
    roll_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    course = models.CharField(max_length=20, choices=COURSE_CHOICES, blank=True, null=True)
    branch = models.CharField(max_length=20, choices=BRANCH_CHOICES, blank=True, null=True)
    year_of_study = models.CharField(max_length=1, choices=YEAR_CHOICES, blank=True, null=True)
    
    #user suspension fields
    suspended = models.BooleanField(default=False, help_text="Suspend user from system")
    suspension_reason = models.TextField(blank=True, help_text="Reason for suspension")
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='suspended_users'
    )
    class Meta:
        db_table = 'auth_user'
    
    def suspend_user(self, admin_user, reason=""):
        """Suspend this user"""
        self.suspended = True
        self.is_active = False  # Also deactivate account
        self.suspension_reason = reason
        self.suspended_by = admin_user
        from django.utils import timezone
        self.suspended_at = timezone.now()
        self.save()
    
    def unsuspend_user(self):
        """Restore user access"""
        self.suspended = False
        self.is_active = True
        self.suspension_reason = ""
        self.suspended_by = None
        self.suspended_at = None
        self.save()

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owned_team')
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_team')
    logo = CloudinaryField('image', folder='sepl/logo/', blank=True)

    purse_remaining = models.IntegerField(default=10000)
    total_purse = models.IntegerField(default=10000)
    max_players = models.IntegerField(default=16)
    iconic_players_count = models.IntegerField(default=0, help_text="Number of iconic players (reduces squad size)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def players_count(self):
        return self.players.count()
    
    def purse_spent(self):
        return self.total_purse - self.purse_remaining
    
    def effective_max_players(self):
        """Get effective squad size after iconic players"""
        return self.max_players - self.iconic_players_count
    
    def can_buy_player(self):
        """Check if team can buy more players (excluding iconic players)"""
        regular_players = self.players.filter(is_iconic=False).count()
        return regular_players < self.effective_max_players()
    
    def slots_remaining(self):
        """Get remaining player slots (excluding iconic players)"""
        regular_players = self.players.filter(is_iconic=False).count()
        return self.effective_max_players() - regular_players
    
    def total_players_count(self):
        """Total players including iconic"""
        return self.players.count()
    
    def regular_players_count(self):
        """Regular players only"""
        return self.players.filter(is_iconic=False).count()

    
class PaddleRaise(models.Model):
    """Track when team owners raise their paddle during auction"""
    auction_session = models.ForeignKey('AuctionSession', on_delete=models.CASCADE, related_name='paddle_raises')
    player = models.ForeignKey('Player', on_delete=models.CASCADE)
    team = models.ForeignKey('Team', on_delete=models.CASCADE)
    amount = models.IntegerField(help_text="Bid amount when paddle was raised")
    raised_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False, help_text="Auctioneer acknowledged this paddle")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-raised_at']
        indexes = [
            models.Index(fields=['player', 'auction_session', '-raised_at']),
            models.Index(fields=['acknowledged', 'auction_session']),
        ]
    
    def __str__(self):
        status = "✓" if self.acknowledged else "⏳"
        return f"{status} {self.team.name} - ₹{self.amount}"

class Player(models.Model):
    PLAYER_CATEGORIES = (
        ('batsman', 'Batsman'),
        ('bowler', 'Bowler'),
        ('all_rounder', 'All Rounder'),
        ('wicket_keeper', 'Wicket Keeper'),
    )
    
    PLAYER_STATUS = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('sold', 'Sold'),
        ('unsold', 'Unsold'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player_profile')
    category = models.CharField(max_length=20, choices=PLAYER_CATEGORIES)
    base_price = models.IntegerField(default=300)
    current_bid = models.IntegerField(default=0)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='players')
    status = models.CharField(max_length=20, choices=PLAYER_STATUS, default='pending')
    batting_style = models.CharField(max_length=50, blank=True)
    bowling_style = models.CharField(max_length=50, blank=True)
    previous_team = models.CharField(max_length=100, blank=True)
    is_iconic = models.BooleanField(
        default=False, 
        help_text="Iconic players (faculty) - free assignment, reduce squad size"
    )
    assigned_at = models.DateTimeField(null=True, blank=True, help_text="When iconic player was assigned")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.category}"
    
    def can_be_iconic(self):
        """Check if player can be assigned as iconic player"""
        return (
            self.user.player_type == 'faculty' and 
            self.status == 'approved' and 
            not self.team and 
            not self.is_iconic
        )
    class Meta:
        ordering = ['-created_at']


class AuctionSession(models.Model):
    SESSION_STATUS = (
        ('upcoming', 'Upcoming'),
        ('live', 'Live'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    )
    
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='upcoming')
    current_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_auction')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    last_bid_team = models.ForeignKey(
        'Team', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='last_bid_sessions',
        help_text="Last team that bid on current player"
    )
    bid_call_count = models.IntegerField(
        default=0, 
        help_text="Number of times auctioneer called 'Going once, twice...'"
    )
    
    
    def __str__(self):
        return f"{self.name} - {self.status}"


class Bid(models.Model):
    auction_session = models.ForeignKey(AuctionSession, on_delete=models.CASCADE, related_name='bids')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='bids')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='bids')
    amount = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['player', 'auction_session', '-amount']),
        ]
    
    def __str__(self):
        return f"{self.team.name} bid {self.amount} for {self.player.user.get_full_name()}"


class AuctionLog(models.Model):
    auction_session = models.ForeignKey(AuctionSession, on_delete=models.CASCADE, related_name='logs')
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    winning_team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True)
    final_amount = models.IntegerField()
    sold = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        if self.sold:
            return f"{self.player.user.get_full_name()} sold to {self.winning_team.name} for {self.final_amount}"
        return f"{self.player.user.get_full_name()} unsold at {self.final_amount}"
    
# Add to auction/models.py

class TournamentBanner(models.Model):
    """Banner images and content for tournament homepage"""
    BANNER_POSITIONS = (
        ('hero', 'Hero Banner (Main)'),
        ('secondary', 'Secondary Banner'),
        ('footer', 'Footer Banner'),
    )
    
    title = models.CharField(max_length=200)
    position = models.CharField(max_length=20, choices=BANNER_POSITIONS, default='hero')
    image = CloudinaryField('image', folder='sepl/banners/')

    heading = models.CharField(max_length=300, blank=True, help_text="Main heading text")
    subheading = models.CharField(max_length=500, blank=True, help_text="Subheading text")
    description = models.TextField(blank=True, help_text="Detailed description")
    button_text = models.CharField(max_length=50, blank=True, help_text="Call-to-action button text")
    button_link = models.CharField(max_length=200, blank=True, help_text="Button URL")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order (lower numbers first)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['position', 'order']
        verbose_name = 'Tournament Banner'
        verbose_name_plural = 'Tournament Banners'
    
    def __str__(self):
        return f"{self.title} ({self.get_position_display()})"


class TournamentContent(models.Model):
    """Dynamic content sections for tournament pages"""
    SECTION_TYPES = (
        ('about', 'About Tournament'),
        ('rules', 'Rules & Regulations'),
        ('schedule', 'Schedule'),
        ('highlights', 'Highlights'),
        ('sponsors', 'Sponsors'),
        ('gallery', 'Gallery'),
        ('custom', 'Custom Section'),
    )
    
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="HTML content supported")
    image = CloudinaryField('image', folder='sepl/banner-content/' , blank=True, null=True)

    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    show_on_homepage = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Tournament Content'
        verbose_name_plural = 'Tournament Content'
    
    def __str__(self):
        return f"{self.title} ({self.get_section_type_display()})"


class TournamentStats(models.Model):
    """Key tournament statistics for homepage display"""
    label = models.CharField(max_length=100, help_text="e.g., 'Total Teams', 'Players Registered'")
    value = models.CharField(max_length=50, help_text="e.g., '8', '120+'")
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class, e.g., 'fas fa-trophy'")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Tournament Statistic'
        verbose_name_plural = 'Tournament Statistics'
    
    def __str__(self):
        return f"{self.label}: {self.value}"


class SocialMediaLink(models.Model):
    """Social media links for tournament"""
    PLATFORMS = (
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter/X'),
        ('instagram', 'Instagram'),
        ('youtube', 'YouTube'),
        ('linkedin', 'LinkedIn'),
        ('whatsapp', 'WhatsApp'),
    )
    
    platform = models.CharField(max_length=20, choices=PLATFORMS)
    url = models.URLField()
    icon_class = models.CharField(max_length=50, blank=True, help_text="FontAwesome class")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        unique_together = ['platform']
    
    def __str__(self):
        return self.get_platform_display()
    
    def get_default_icon(self):
        icons = {
            'facebook': 'fab fa-facebook',
            'twitter': 'fab fa-twitter',
            'instagram': 'fab fa-instagram',
            'youtube': 'fab fa-youtube',
            'linkedin': 'fab fa-linkedin',
            'whatsapp': 'fab fa-whatsapp',
        }
        return icons.get(self.platform, 'fas fa-link')
