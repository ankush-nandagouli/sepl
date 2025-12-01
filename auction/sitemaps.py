
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Team, Player, AuctionSession, TournamentBanner, TournamentContent
from django.contrib.sitemaps import Sitemap
from django.urls import get_resolver

class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 0.8
    changefreq = 'daily'
    
    def items(self):
        return ['home', 'register', 'login', 'player_registration']
    
    def location(self, item):
        return reverse(item)


class TeamSitemap(Sitemap):
    """Sitemap for team pages"""
    changefreq = "weekly"
    priority = 0.7
    
    def items(self):
        return Team.objects.all()
    
    def lastmod(self, obj):
        return obj.created_at
    
    def location(self, obj):
        # If you have team detail pages, return their URLs
        # For now, just return home since teams are shown there
        return reverse('home')


class PlayerSitemap(Sitemap):
    """Sitemap for approved players"""
    changefreq = "weekly"
    priority = 0.6
    
    def items(self):
        return Player.objects.filter(status='approved')
    
    def lastmod(self, obj):
        return obj.created_at
    
    def location(self, obj):
        # If you have player detail pages, return their URLs
        # For now, just return home since players are shown there
        return reverse('home')
        
class AuctionSessionSitemap(Sitemap):
    """Sitemap for auction sessions"""
    changefreq = "daily"
    priority = 0.9
    
    def items(self):
        return AuctionSession.objects.filter(status='live')
    
    def lastmod(self, obj):
        return obj.created_at
    
    def location(self, obj):
        return reverse('home')


class TournamentContentSitemap(Sitemap):
    """Sitemap for tournament content pages"""
    changefreq = "weekly"
    priority = 0.7
    
    def items(self):
        return TournamentContent.objects.filter(is_active=True)
    
    def lastmod(self, obj):
        return obj.updated_at
    
    def location(self, obj):
        return reverse('home')




class DashboardSitemap(Sitemap):
    """Sitemap for dashboard pages (for authenticated users)"""
    priority = 0.7
    changefreq = 'daily'
    
    def items(self):
        # Return dashboard URLs that should be in sitemap
        return [
            'dashboard',
            'player_dashboard',
            'owner_dashboard',
            'manager_dashboard',
            'admin_dashboard',
            'auctioneer_dashboard',
        ]
    
    def location(self, item):
        try:
            return reverse(item)
        except:
            return reverse('home')


class DynamicViewSitemap(Sitemap):
    """Auto-generate sitemap for all named GET URLs."""
    priority = 0.7
    changefreq = 'daily'

    EXCLUDE_NAMES = [
        'approve_player', 'reject_player', 'start_auction_session', 'end_auction_session',
        'auctioneer_quick_bid', 'auctioneer_start_player', 'auctioneer_complete_sale',
        'auctioneer_call_going', 'auctioneer_team_info',  # AJAX endpoints
        'delete_user', 'suspend_user', 'unsuspend_user', 'revoke_permissions',
        'reorder_banners', 'toggle_banner', 'delete_banner',  # Admin AJAX
    ]

    def items(self):
        """Get all usable URL names from urlpatterns."""
        url_names = []
        resolver = get_resolver()
        for pattern in resolver.url_patterns:
            if pattern.name and pattern.name not in self.EXCLUDE_NAMES:
                url_names.append(pattern.name)
        return url_names

    def location(self, item):
        return reverse(item)
