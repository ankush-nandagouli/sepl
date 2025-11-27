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
    
    # Team Owner URLs
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/auction/', views.live_auction, name='live_auction'),
    
    # Team Manager URLs
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    
    # Umpire URLs
    path('umpire/dashboard/', views.umpire_dashboard, name='umpire_dashboard'),
]