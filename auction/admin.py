# auction/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Team, Player, AuctionSession, Bid, AuctionLog, PaddleRaise

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'user_type', 'player_type_display', 'profile_pic_display']
    list_filter = ['user_type', 'player_type', 'course', 'branch', 'is_staff', 'is_active', 'suspended']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'roll_number']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile Information', {
            'fields': ('profile_picture', 'phone', 'college')
        }),
        ('Player Information', {
            'fields': ('user_type', 'player_type', 'roll_number', 'course', 'branch', 'year_of_study'),
            'classes': ('collapse',),
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profile Information', {
            'fields': ('profile_picture', 'phone', 'college')
        }),
        ('Player Information', {
            'fields': ('user_type', 'player_type', 'roll_number', 'course', 'branch', 'year_of_study'),
        }),
    )
    
    def player_type_display(self, obj):
        if obj.user_type == 'player' and obj.player_type:
            return obj.get_player_type_display()
        return '-'
    player_type_display.short_description = 'Player Type'
    
    def profile_pic_display(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />', obj.profile_picture.url)
        return '-'
    profile_pic_display.short_description = 'Profile Picture'

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'purse_remaining', 'total_purse', 'players_count', 'max_players', 'slots_remaining']
    list_filter = ['created_at']
    search_fields = ['name', 'owner__username']
    readonly_fields = ['created_at', 'purse_spent']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'owner', 'manager', 'logo')
        }),
        ('Financial Details', {
            'fields': ('total_purse', 'purse_remaining', 'purse_spent')
        }),
        ('Team Limits', {
            'fields': ('max_players',),
            'description': 'Maximum number of players this team can have'
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def purse_spent(self, obj):
        return f"₹{obj.purse_spent()}"
    purse_spent.short_description = 'Purse Spent'
    
    def slots_remaining(self, obj):
        return f"{obj.slots_remaining()}/{obj.max_players}"
    slots_remaining.short_description = 'Slots Remaining'

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['player_name', 'player_type_display', 'category', 'status', 'team', 'base_price', 'current_bid', 'profile_pic']
    list_filter = ['status', 'category', 'team', 'user__player_type', 'user__course', 'user__branch']
    search_fields = ['user__first_name', 'user__last_name', 'user__username', 'user__roll_number']
    readonly_fields = ['created_at', 'current_bid']
    actions = ['approve_players', 'reject_players', 'reset_players']
    
    fieldsets = (
        ('Player Information', {
            'fields': ('user', 'category', 'status')
        }),
        ('Cricket Skills', {
            'fields': ('batting_style', 'bowling_style', 'previous_team')
        }),
        ('Auction Details', {
            'fields': ('base_price', 'current_bid', 'team')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def player_name(self, obj):
        return obj.user.get_full_name()
    player_name.short_description = 'Player Name'
    player_name.admin_order_field = 'user__first_name'
    
    def player_type_display(self, obj):
        if obj.user.player_type:
            return obj.user.get_player_type_display()
        return '-'
    player_type_display.short_description = 'Type'
    
    def profile_pic(self, obj):
        if obj.user.profile_picture:
            return format_html('<img src="{}" width="40" height="40" style="border-radius: 50%; object-fit: cover;" />', obj.user.profile_picture.url)
        return '-'
    profile_pic.short_description = 'Photo'
    
    def approve_players(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} player(s) approved.')
    approve_players.short_description = "Approve selected players"
    
    def reject_players(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} player(s) rejected.')
    reject_players.short_description = "Reject selected players"
    
    def reset_players(self, request, queryset):
        updated = queryset.update(status='approved', current_bid=0, team=None)
        self.message_user(request, f'{updated} player(s) reset to available status.')
    reset_players.short_description = "Reset players (set to approved, remove team)"

@admin.register(AuctionSession)
class AuctionSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'current_player', 'last_bid_team', 'bid_call_count','started_at', 'ended_at']
    list_filter = ['status', 'started_at']
    readonly_fields = ['created_at', 'bid_call_count']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('name', 'status')
        }),
        ('Current State', {
            'fields': ('current_player', 'last_bid_team', 'bid_call_count')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'ended_at', 'created_at')
        }),
    )

@admin.register(PaddleRaise)
class PaddleRaiseAdmin(admin.ModelAdmin):
    list_display = ['team_name', 'player_name', 'amount', 'acknowledged', 'raised_at']
    list_filter = ['acknowledged', 'auction_session', 'team', 'raised_at']
    search_fields = ['team__name', 'player__user__first_name', 'player__user__last_name']
    readonly_fields = ['raised_at', 'acknowledged_at']
    date_hierarchy = 'raised_at'
    
    def team_name(self, obj):
        return obj.team.name
    team_name.short_description = 'Team'
    team_name.admin_order_field = 'team__name'
    
    def player_name(self, obj):
        return obj.player.user.get_full_name()
    player_name.short_description = 'Player'
    
    actions = ['mark_acknowledged', 'mark_unacknowledged']
    
    def mark_acknowledged(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(acknowledged=True, acknowledged_at=timezone.now())
        self.message_user(request, f'{updated} paddle raise(s) marked as acknowledged.')
    mark_acknowledged.short_description = "Mark as acknowledged"
    
    def mark_unacknowledged(self, request, queryset):
        updated = queryset.update(acknowledged=False, acknowledged_at=None)
        self.message_user(request, f'{updated} paddle raise(s) marked as unacknowledged.')
    mark_unacknowledged.short_description = "Mark as unacknowledged"


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['player_name', 'team', 'amount', 'timestamp', 'session']
    list_filter = ['team', 'auction_session', 'timestamp']
    search_fields = ['player__user__first_name', 'player__user__last_name', 'team__name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def player_name(self, obj):
        return obj.player.user.get_full_name()
    player_name.short_description = 'Player'
    
    def session(self, obj):
        return obj.auction_session.name
    session.short_description = 'Auction Session'

@admin.register(AuctionLog)
class AuctionLogAdmin(admin.ModelAdmin):
    list_display = ['player_name', 'winning_team', 'final_amount', 'sold', 'timestamp', 'session']
    list_filter = ['sold', 'auction_session', 'timestamp']
    search_fields = ['player__user__first_name', 'player__user__last_name', 'winning_team__name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def player_name(self, obj):
        return obj.player.user.get_full_name()
    player_name.short_description = 'Player'
    
    def session(self, obj):
        return obj.auction_session.name
    session.short_description = 'Auction Session'
    
    
# Add to auction/admin.py

from .models import TournamentBanner, TournamentContent, TournamentStats, SocialMediaLink

@admin.register(TournamentBanner)
class TournamentBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'position', 'is_active', 'order', 'image_preview', 'updated_at']
    list_filter = ['position', 'is_active', 'created_at']
    search_fields = ['title', 'heading', 'subheading']
    list_editable = ['is_active', 'order']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'position', 'order', 'is_active')
        }),
        ('Banner Image', {
            'fields': ('image',)
        }),
        ('Text Content', {
            'fields': ('heading', 'subheading', 'description'),
            'description': 'Text overlays for the banner'
        }),
        ('Call to Action', {
            'fields': ('button_text', 'button_link'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="60" style="object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(TournamentContent)
class TournamentContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'section_type', 'is_active', 'show_on_homepage', 'order', 'image_preview']
    list_filter = ['section_type', 'is_active', 'show_on_homepage']
    search_fields = ['title', 'content']
    list_editable = ['is_active', 'show_on_homepage', 'order']
    
    fieldsets = (
        ('Section Details', {
            'fields': ('section_type', 'title', 'order')
        }),
        ('Content', {
            'fields': ('content', 'image'),
            'description': 'HTML is supported in content field'
        }),
        ('Display Settings', {
            'fields': ('is_active', 'show_on_homepage')
        }),
    )
    
    class Media:
        css = {
            'all': ('admin/css/forms.css',)
        }
        js = ('admin/js/vendor/jquery/jquery.js',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Image'


@admin.register(TournamentStats)
class TournamentStatsAdmin(admin.ModelAdmin):
    list_display = ['label', 'value', 'icon', 'order', 'is_active']
    list_editable = ['value', 'order', 'is_active']
    search_fields = ['label', 'value']
    
    fieldsets = (
        (None, {
            'fields': ('label', 'value', 'icon', 'order', 'is_active'),
            'description': 'Stats displayed on homepage. Use FontAwesome icons (e.g., fas fa-trophy)'
        }),
    )


@admin.register(SocialMediaLink)
class SocialMediaLinkAdmin(admin.ModelAdmin):
    list_display = ['platform', 'url', 'icon_display', 'is_active', 'order']
    list_filter = ['platform', 'is_active']
    list_editable = ['is_active', 'order']
    
    fieldsets = (
        (None, {
            'fields': ('platform', 'url', 'icon_class', 'order', 'is_active')
        }),
    )
    
    def icon_display(self, obj):
        icon = obj.icon_class or obj.get_default_icon()
        return format_html('<i class="{}"></i>', icon)
    icon_display.short_description = 'Icon'