from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
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
    
    
    # NEW: User Management URLs
    path('admin/users/', views.manage_users, name='manage_users'),
    path('admin/users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('admin/users/<int:user_id>/suspend/', views.suspend_user, name='suspend_user'),
    path('admin/users/<int:user_id>/unsuspend/', views.unsuspend_user, name='unsuspend_user'),
    path('admin/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('admin/users/<int:user_id>/revoke/', views.revoke_permissions, name='revoke_permissions'),
    
    
    # NEW: Auctioneer URLs
    path('auctioneer/dashboard/', views.auctioneer_dashboard, name='auctioneer_dashboard'),
    path('auctioneer/quick-bid/', views.auctioneer_quick_bid, name='auctioneer_quick_bid'),
    path('auctioneer/start-player/', views.auctioneer_start_player, name='auctioneer_start_player'),
    path('auctioneer/complete-sale/', views.auctioneer_complete_sale, name='auctioneer_complete_sale'),
    path('auctioneer/call-going/', views.auctioneer_call_going, name='auctioneer_call_going'),
    path('auctioneer/team/<int:team_id>/', views.auctioneer_team_info, name='auctioneer_team_info'),
    
    # Team Owner URLs
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/auction/', views.live_auction, name='live_auction'),
    
    # Team Manager URLs
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    
    # Umpire URLs
    path('umpire/dashboard/', views.umpire_dashboard, name='umpire_dashboard'),
]