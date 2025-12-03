from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from .sitemaps import (
    StaticViewSitemap, 
    TeamSitemap, 
    PlayerSitemap, 
    AuctionSessionSitemap,
    TournamentContentSitemap,
    DynamicViewSitemap
)
from . import views

# Sitemap configuration
sitemaps = {
    'static': StaticViewSitemap,
    'teams': TeamSitemap,
    'players': PlayerSitemap,
    'auctions': AuctionSessionSitemap,
    'content': TournamentContentSitemap,
    'pages': DynamicViewSitemap,
}

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
   
    path('teams/', views.team_list, name='team_list'),
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    #edit profile
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    # Player URLs
    path('player/register/', views.player_registration, name='player_registration'),
    path('player/dashboard/', views.player_dashboard, name='player_dashboard'),
    
    # Admin URLs
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/teams/', views.manage_teams, name='manage_teams'),
    path('admin/players/', views.manage_players, name='manage_players'),
    path('admin/players/<int:player_id>/approve/', views.approve_player, name='approve_player'),
    path('admin/players/<int:player_id>/reject/', views.reject_player, name='reject_player'),
    path('admin/auction/', views.manage_auction, name='manage_auction'),
    path('admin/auction/<int:session_id>/start/', views.start_auction_session, name='start_auction_session'),
    path('admin/auction/<int:session_id>/end/', views.end_auction_session, name='end_auction_session'),
    path('admin/auction/control/', views.auction_control, name='auction_control'),
    
    
    # User Management URLs
    path('admin/users/', views.manage_users, name='manage_users'),
    path('admin/users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('admin/users/<int:user_id>/suspend/', views.suspend_user, name='suspend_user'),
    path('admin/users/<int:user_id>/unsuspend/', views.unsuspend_user, name='unsuspend_user'),
    path('admin/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('admin/users/<int:user_id>/revoke/', views.revoke_permissions, name='revoke_permissions'),
    
    # Iconic Player Management (Admin)
    path('admin/iconic-players/', views.manage_iconic_players, name='manage_iconic_players'),
    path('admin/iconic-players/assign/', views.assign_iconic_player, name='assign_iconic_player'),
    path('admin/iconic-players/remove/', views.remove_iconic_player, name='remove_iconic_player'),
    path('admin/iconic-players/team/<int:team_id>/', views.get_team_iconic_info, name='get_team_iconic_info'),
    
    # Banner Management URLs
    path('admin/banners/', views.manage_banners, name='manage_banners'),
    path('admin/banners/<int:banner_id>/edit/', views.edit_banner, name='edit_banner'),
    path('admin/banners/<int:banner_id>/delete/', views.delete_banner, name='delete_banner'),
    path('admin/banners/<int:banner_id>/toggle/', views.toggle_banner, name='toggle_banner'),
    path('admin/banners/reorder/', views.reorder_banners, name='reorder_banners'),
    
    # Auctioneer URLs
    path('auctioneer/dashboard/', views.auctioneer_dashboard, name='auctioneer_dashboard'),
    path('auctioneer/quick-bid/', views.auctioneer_quick_bid, name='auctioneer_quick_bid'),
    path('auctioneer/start-player/', views.auctioneer_start_player, name='auctioneer_start_player'),
    path('auctioneer/complete-sale/', views.auctioneer_complete_sale, name='auctioneer_complete_sale'),
    path('auctioneer/call-going/', views.auctioneer_call_going, name='auctioneer_call_going'),
    path('auctioneer/team/<int:team_id>/', views.auctioneer_team_info, name='auctioneer_team_info'),
    
    # Team Owner URLs
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/auction/', views.live_auction, name='live_auction'),
    path('owner/my-team/', views.my_team, name='my_team'),
    path('owner/player/<int:player_id>/', views.player_profile, name='player_profile'),
    
    # ========================================
    # ADMIN TEAM MANAGEMENT
    # ========================================
    path('admin/teams/overview/', views.admin_team_overview, name='admin_team_overview'),
    path('admin/teams/<int:team_id>/detail/', views.admin_team_detail, name='admin_team_detail'),
    path('admin/teams/<int:team_id>/edit/', views.admin_edit_team, name='admin_edit_team'),
    path('admin/teams/<int:team_id>/delete/', views.admin_delete_team, name='admin_delete_team'),
    path('admin/teams/<int:team_id>/reset/', views.admin_reset_team, name='admin_reset_team'),
    path('admin/teams/<int:team_id>/remove-player/<int:player_id>/', views.admin_remove_player_from_team, name='admin_remove_player_from_team'),
    
    # Team Manager URLs
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    
    # Umpire URLs
    path('umpire/dashboard/', views.umpire_dashboard, name='umpire_dashboard'),
    
        # SEO URLs - Django Sitemap
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
]