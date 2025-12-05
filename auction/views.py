
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .models import User, Team, Player, AuctionSession, Bid, AuctionLog, TournamentBanner, TournamentContent, TournamentStats, SocialMediaLink, PaddleRaise
from .forms import UserRegistrationForm, PlayerRegistrationForm, TeamCreationForm, AuctionSessionForm, UserProfileEditForm, PlayerProfileEditForm, PlayerDetailsEditForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .utils import broadcast_bid_update, broadcast_player_update, broadcast_bidding_end
import json
from django.db import transaction
import csv


def is_admin(user):
    return user.user_type == 'admin'

def is_team_owner(user):
    return user.user_type == 'team_owner'

def is_player(user):
    return user.user_type == 'player'

def is_auctioneer(user):
    return user.user_type == 'auctioneer'

def home(request):
    """Homepage for Satpuda Engineering Premier League with dynamic banners"""
    teams = Team.objects.all()
    total_players = Player.objects.filter(status='approved').count()
    active_session = AuctionSession.objects.filter(status='live').first()
    
    # Get active banners
    hero_banners = TournamentBanner.objects.filter(
        position='hero', 
        is_active=True
    ).order_by('order')
    
    secondary_banners = TournamentBanner.objects.filter(
        position='secondary',
        is_active=True
    ).order_by('order')

    footer_banners = TournamentBanner.objects.filter(
        position='footer',
        is_active=True
    ).order_by('order')

    # Get content sections for homepage
    content_sections = TournamentContent.objects.filter(
        is_active=True,
        show_on_homepage=True
    ).order_by('order')
    
    # Get tournament stats
    tournament_stats = TournamentStats.objects.filter(
        is_active=True
    ).order_by('order')
    
    # Get social media links
    social_links = SocialMediaLink.objects.filter(
        is_active=True
    ).order_by('order')
    
    # Get latest auction logs for highlights
    recent_sales = AuctionLog.objects.filter(
        sold=True
    ).select_related('player__user', 'winning_team').order_by('-timestamp')[:5]
    
    context = {
        'teams': teams,
        'total_players': total_players,
        'active_session': active_session,
        'hero_banners': hero_banners,
        'secondary_banners': secondary_banners,
        'footer_banners': footer_banners,
        'content_sections': content_sections,
        'tournament_stats': tournament_stats,
        'social_links': social_links,
        'recent_sales': recent_sales,
    }
    return render(request, 'home.html', context)

def register(request):
    """User registration with proper validation and debugging"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Debug: Print all POST data
        print("=" * 80)
        print("REGISTRATION FORM SUBMITTED")
        print("=" * 80)
        print("POST Data:")
        for key, value in request.POST.items():
            if 'password' not in key.lower():  # Don't print passwords
                print(f"  {key}: {value}")
        print("=" * 80)
        
        form = UserRegistrationForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                user = form.save()
                print(f"SUCCESS: User '{user.username}' created successfully!")
                print(f"  - User Type: {user.user_type}")
                if user.user_type == 'player':
                    print(f"  - Player Type: {user.player_type}")
                    print(f"  - Course: {user.course}")
                    print(f"  - Branch: {user.branch}")
                    print(f"  - Year: {user.year_of_study}")
                print("=" * 80)
                
                messages.success(request, f'Account created successfully! Please login.')
                return redirect('login')
            except Exception as e:
                print(f"ERROR during save: {str(e)}")
                print("=" * 80)
                messages.error(request, f'Error creating account: {str(e)}')
        else:
            # Display form errors
            print("FORM VALIDATION ERRORS:")
            print("-" * 80)
            
            # Field errors
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"  {field}: {error}")
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields[field].label if field in form.fields else field
                        messages.error(request, f'{field_label}: {error}')
            
            # Print form data for debugging
            print("-" * 80)
            print("Form Data (cleaned_data):")
            for field, value in form.cleaned_data.items():
                if 'password' not in field.lower():
                    print(f"  {field}: {value}")
            print("=" * 80)
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})
def user_login(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'registration/login.html')

@login_required
def user_logout(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('home')

@login_required
def dashboard(request):
    """Dashboard - redirects based on user type"""
    user = request.user
    user_type = getattr(user, 'user_type', None)

    redirect_map = {
        'admin': 'admin_dashboard',
        'team_owner': 'owner_dashboard',
        'player': 'player_dashboard',
        'team_manager': 'manager_dashboard',
        'umpire': 'umpire_dashboard',
        'auctioneer': 'auctioneer_dashboard',
    }

    if user_type in redirect_map:
        return redirect(redirect_map[user_type])

    return render(request, 'dashboard.html')

# ADMIN VIEWS
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard with overview"""
    total_teams = Team.objects.count()
    total_players = Player.objects.count()
    approved_players = Player.objects.filter(status='approved').count()
    pending_players = Player.objects.filter(status='pending').count()
    sold_players = Player.objects.filter(status='sold').count()
    
    active_session = AuctionSession.objects.filter(status='live').first()
    
    teams = Team.objects.annotate(
        player_count=Count('players'),
        total_spent=Sum('players__current_bid')
    )
    
    recent_logs = AuctionLog.objects.select_related('player', 'winning_team').order_by('-timestamp')[:10]
    
    context = {
        'total_teams': total_teams,
        'total_players': total_players,
        'approved_players': approved_players,
        'pending_players': pending_players,
        'sold_players': sold_players,
        'active_session': active_session,
        'teams': teams,
        'recent_logs': recent_logs,
    }
    return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def manage_teams(request):
    """Manage teams"""
    if request.method == 'POST':
        form = TeamCreationForm(request.POST, request.FILES)
        if form.is_valid():
            team = form.save()
            messages.success(request, f'Team {team.name} created successfully!')
            return redirect('manage_teams')
    else:
        form = TeamCreationForm()
    
    teams = Team.objects.select_related('owner').annotate(player_count=Count('players'))
    context = {
        'form': form,
        'teams': teams,
    }
    return render(request, 'admin/manage_teams.html', context)

@login_required
@user_passes_test(is_admin)
def manage_players(request):
    """Manage player approvals"""
    pending_players = Player.objects.filter(status='pending').select_related('user')
    approved_players = Player.objects.filter(status='approved').select_related('user')
    
    context = {
        'pending_players': pending_players,
        'approved_players': approved_players,
    }
    return render(request, 'admin/manage_players.html', context)

@login_required
@user_passes_test(is_admin)
def approve_player(request, player_id):
    """Approve a player"""
    player = get_object_or_404(Player, id=player_id)
    player.status = 'approved'
    player.save()
    messages.success(request, f'{player.user.get_full_name()} approved!')
    return redirect('manage_players')

@login_required
@user_passes_test(is_admin)
def reject_player(request, player_id):
    """Reject a player"""
    player = get_object_or_404(Player, id=player_id)
    player.status = 'rejected'
    player.save()
    messages.warning(request, f'{player.user.get_full_name()} rejected!')
    return redirect('manage_players')

@login_required
@user_passes_test(is_admin)
def manage_auction(request):
    """Auction control panel"""
    if request.method == 'POST':
        form = AuctionSessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            messages.success(request, f'Auction session "{session.name}" created!')
            return redirect('manage_auction')
    else:
        form = AuctionSessionForm()
    
    sessions = AuctionSession.objects.all().order_by('-created_at')
    active_session = sessions.filter(status='live').first()
    available_players = Player.objects.filter(status='approved')
    
    context = {
        'form': form,
        'sessions': sessions,
        'active_session': active_session,
        'available_players': available_players,
    }
    return render(request, 'admin/manage_auction.html', context)

@login_required
@user_passes_test(is_admin)
def start_auction_session(request, session_id):
    """Start an auction session"""
    session = get_object_or_404(AuctionSession, id=session_id)
    
    # End any other active sessions
    AuctionSession.objects.filter(status='live').update(status='paused')
    
    session.status = 'live'
    session.started_at = timezone.now()
    session.save()
    
    messages.success(request, f'Auction session "{session.name}" started!')
    return redirect('auction_control')

@login_required
@user_passes_test(is_admin)
def end_auction_session(request, session_id):
    """End an auction session"""
    session = get_object_or_404(AuctionSession, id=session_id)
    session.status = 'completed'
    session.ended_at = timezone.now()
    session.save()
    
    messages.success(request, f'Auction session "{session.name}" ended!')
    return redirect('manage_auction')

@login_required
@user_passes_test(is_admin)
def auction_control(request):
    """Live auction control room with search functionality"""
    active_session = AuctionSession.objects.filter(status='live').first()
    
    if not active_session:
        messages.warning(request, 'No active auction session!')
        return redirect('manage_auction')
    
    available_players = Player.objects.filter(status='approved').select_related('user')
    teams = Team.objects.all()
    current_bids = []
    
    if active_session.current_player:
        current_bids = Bid.objects.filter(
            player=active_session.current_player,
            auction_session=active_session
        ).select_related('team').order_by('-amount')[:5]
    
    context = {
        'session': active_session,
        'available_players': available_players,
        'teams': teams,
        'current_player': active_session.current_player,
        'current_bids': current_bids,
    }
    return render(request, 'admin/auction_control.html', context)

# PLAYER VIEWS
@login_required
@user_passes_test(is_player)
def player_registration(request):
    """Player self-registration"""
    if hasattr(request.user, 'player_profile'):
        messages.info(request, 'You have already registered as a player!')
        return redirect('player_dashboard')
    
    if request.method == 'POST':
        form = PlayerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            player = form.save(commit=False)
            player.user = request.user
            player.save()
            messages.success(request, 'Player registration submitted! Awaiting admin approval.')
            return redirect('player_dashboard')
    else:
        form = PlayerRegistrationForm()
    
    return render(request, 'player/register.html', {'form': form})

@login_required
def player_dashboard(request):
    """Player dashboard"""
    try:
        player = request.user.player_profile
        bids = Bid.objects.filter(player=player).select_related('team')[:5]
    except Player.DoesNotExist:
        player = None
        bids = []
    
    context = {
        'player': player,
        'recent_bids': bids,
    }
    return render(request, 'player/dashboard.html', context)

# TEAM OWNER VIEWS
@login_required
@user_passes_test(is_team_owner)
def owner_dashboard(request):
    """Team owner dashboard"""
    try:
        team = request.user.owned_team
    except Team.DoesNotExist:
        team = None
        return render(request, 'owner/no_team.html')
    
    if not team:
        return render(request, 'owner/no_team.html')
    
    players = team.players.all().select_related('user')
    
    squad_stats = {
        'batsman': players.filter(category='batsman').count(),
        'bowler': players.filter(category='bowler').count(),
        'all_rounder': players.filter(category='all_rounder').count(),
        'wicket_keeper': players.filter(category='wicket_keeper').count(),
    }
    
    recent_bids = Bid.objects.filter(team=team).select_related('player').order_by('-timestamp')[:10]
    
    context = {
        'team': team,
        'players': players,
        'squad_stats': squad_stats,
        'recent_bids': recent_bids,
    }
    return render(request, 'owner/dashboard.html', context)

@login_required
@user_passes_test(is_team_owner)
def live_auction(request):
    """Live auction participation for team owners"""
    try:
        team = request.user.owned_team
    except Team.DoesNotExist:
        return redirect('owner_dashboard')
    
    active_session = AuctionSession.objects.filter(status='live').first()
    
    if not active_session:
        return render(request, 'owner/no_auction.html')
    
    all_teams = Team.objects.exclude(id=team.id)
    
    context = {
        'team': team,
        'session': active_session,
        'current_player': active_session.current_player,
        'all_teams': all_teams,
    }
    return render(request, 'owner/live_auction.html', context)

# MANAGER VIEWS
@login_required
def manager_dashboard(request):
    """Team manager dashboard"""
    try:
        team = request.user.managed_team
        players = team.players.all().select_related('user')
    except:
        team = None
        players = []
    
    context = {
        'team': team,
        'players': players,
    }
    return render(request, 'manager/dashboard.html', context)

# UMPIRE VIEWS
@login_required
def umpire_dashboard(request):
    """Umpire dashboard"""
    return render(request, 'umpire/dashboard.html')





@login_required
def edit_profile(request):
    """Edit user profile - adapts form based on user type"""
    user = request.user
    
    # Determine which form to use
    if user.user_type == 'player':
        ProfileForm = PlayerProfileEditForm
    else:
        ProfileForm = UserProfileEditForm
    
    # Check if user has player profile
    try:
        player_profile = user.player_profile
        has_player_profile = True
    except Player.DoesNotExist:
        player_profile = None
        has_player_profile = False
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'profile':
            profile_form = ProfileForm(request.POST, request.FILES, instance=user)
            
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('edit_profile')
            else:
                messages.error(request, 'Please correct the errors below.')
        
        elif form_type == 'player_details' and has_player_profile:
            player_form = PlayerDetailsEditForm(request.POST, instance=player_profile)
            
            if player_form.is_valid():
                player_form.save()
                messages.success(request, 'Cricket details updated successfully!')
                return redirect('edit_profile')
            else:
                messages.error(request, 'Please correct the errors below.')
        
        elif form_type == 'password':
            password_form = PasswordChangeForm(user, request.POST)
            
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, 'Password changed successfully!')
                return redirect('edit_profile')
            else:
                messages.error(request, 'Please correct the errors below.')
    
    # Initialize forms for GET request
    profile_form = ProfileForm(instance=user)
    password_form = PasswordChangeForm(user)
    player_form = PlayerDetailsEditForm(instance=player_profile) if has_player_profile else None
    
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'player_form': player_form,
        'has_player_profile': has_player_profile,
    }
    return render(request, 'profile/edit_profile.html', context)






@login_required
@user_passes_test(is_admin)
def manage_users(request):
    """Admin page to manage all users"""
    query = request.GET.get('q', '')
    user_type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    
    users = User.objects.all().exclude(id=request.user.id).order_by('-date_joined')
    
    # Search
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(roll_number__icontains=query)
        )
    
    # Filter by user type
    if user_type_filter:
        users = users.filter(user_type=user_type_filter)
    
    # Filter by status
    if status_filter == 'active':
        users = users.filter(is_active=True, suspended=False)
    elif status_filter == 'suspended':
        users = users.filter(suspended=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    context = {
        'users': users,
        'query': query,
        'user_type_filter': user_type_filter,
        'status_filter': status_filter,
        'total_users': User.objects.count() - 1,  # Exclude current admin
        'active_users': User.objects.filter(is_active=True, suspended=False).count(),
        'suspended_users': User.objects.filter(suspended=True).count(),
    }
    return render(request, 'admin/manage_users.html', context)


@login_required
@user_passes_test(is_admin)
def suspend_user(request, user_id):
    """Suspend a user"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        
        if user.is_superuser:
            messages.error(request, 'Cannot suspend superuser accounts!')
            return redirect('manage_users')
        
        reason = request.POST.get('reason', 'Violated tournament rules')
        user.suspend_user(request.user, reason)
        
        messages.warning(request, f'User {user.get_full_name()} has been suspended!')
        return redirect('manage_users')
    
    return redirect('manage_users')


@login_required
@user_passes_test(is_admin)
def unsuspend_user(request, user_id):
    """Restore user access"""
    user = get_object_or_404(User, id=user_id)
    user.unsuspend_user()
    
    messages.success(request, f'User {user.get_full_name()} has been restored!')
    return redirect('manage_users')


@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """Delete a user (with confirmation)"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        
        if user.is_superuser:
            messages.error(request, 'Cannot delete superuser accounts!')
            return redirect('manage_users')
        
        username = user.username
        user.delete()
        
        messages.success(request, f'User {username} has been permanently deleted!')
        return redirect('manage_users')
    
    return redirect('manage_users')


@login_required
@user_passes_test(is_admin)
def revoke_permissions(request, user_id):
    """Change user type / revoke specific permissions"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        new_user_type = request.POST.get('user_type')
        
        if new_user_type in dict(User.USER_TYPES):
            old_type = user.get_user_type_display()
            user.user_type = new_user_type
            user.save()
            
            messages.success(
                request, 
                f'Changed {user.get_full_name()} from {old_type} to {user.get_user_type_display()}'
            )
        else:
            messages.error(request, 'Invalid user type!')
        
        return redirect('manage_users')
    
    return redirect('manage_users')


@login_required
@user_passes_test(is_admin)
def user_detail(request, user_id):
    """View detailed user information"""
    user = get_object_or_404(User, id=user_id)
    
    # Get related data
    owned_team = None
    managed_team = None
    player_profile = None
    
    try:
        owned_team = user.owned_team
    except:
        pass
    
    try:
        managed_team = user.managed_team
    except:
        pass
    
    try:
        player_profile = user.player_profile
    except:
        pass
    
    context = {
        'viewed_user': user,
        'owned_team': owned_team,
        'managed_team': managed_team,
        'player_profile': player_profile,
    }
    return render(request, 'admin/user_detail.html', context)




@login_required
@user_passes_test(is_auctioneer)
def auctioneer_dashboard(request):
    """Auctioneer control center - UPDATED to exclude iconic players from auction"""
    active_session = AuctionSession.objects.filter(status='live').first()
    
    if not active_session:
        sessions = AuctionSession.objects.filter(
            status__in=['upcoming', 'paused']
        ).order_by('-created_at')
        return render(request, 'auctioneer/no_auction.html', {
            'sessions': sessions
        })
    
    current_player = active_session.current_player
    current_bids_qs = Bid.objects.none()
    paddle_raises = []

    if current_player:
        current_bids_qs = Bid.objects.filter(
            player=current_player,
            auction_session=active_session
        ).select_related('team').order_by('-amount')
        current_bids = list(current_bids_qs[:5])
        
        paddle_raises = PaddleRaise.objects.filter(
            player=current_player,
            auction_session=active_session,
            acknowledged=False
        ).select_related('team').order_by('raised_at')
    else:
        current_bids = []

    # Team Stats
    team_stats = []
    teams = Team.objects.annotate(
        player_count=Count('players')
    ).select_related('owner').order_by('name')

    for team in teams:
        last_bid = current_bids_qs.filter(team=team).first() if current_player else None
        next_bid_increment = 50 if (current_player and current_player.current_bid < 700) else 100
        next_bid_val = current_player.current_bid + next_bid_increment if current_player else 0
        
        # Calculate effective slots considering iconic players
        iconic_count = team.players.filter(user__player_type='faculty').count()
        effective_max = team.max_players - iconic_count
        regular_count = team.players.exclude(user__player_type='faculty').count()
        slots_left = effective_max - regular_count

        stats = {
            'team': team,
            'purse_remaining': team.purse_remaining,
            'purse_percentage': (team.purse_remaining / team.total_purse * 100) if team.total_purse else 0,
            'players_count': regular_count,
            'iconic_count': iconic_count,
            'slots_remaining': slots_left,
            'can_bid': current_player and slots_left > 0 and team.purse_remaining >= next_bid_val,
            'last_bid': last_bid,
        }
        team_stats.append(stats)
        
    # CRITICAL FIX: Exclude iconic players (faculty) from available players
    search_query = request.GET.get('search', '').strip()
    
    if search_query:
        available_players = Player.objects.filter(
            status='approved'
        ).exclude(
            user__player_type='faculty'  # EXCLUDE ICONIC PLAYERS
        ).filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__roll_number__icontains=search_query) |
            Q(category__icontains=search_query)
        ).select_related('user').order_by('base_price')
    else:
        available_players = Player.objects.filter(
            status='approved'
        ).exclude(
            user__player_type='faculty'  # EXCLUDE ICONIC PLAYERS
        ).select_related('user').order_by('base_price')[:20]

    recent_sales = AuctionLog.objects.filter(
        auction_session=active_session
    ).select_related('player__user', 'winning_team').order_by('-timestamp')[:10]

    return render(request, 'auctioneer/dashboard.html', {
        'session': active_session,
        'current_player': current_player,
        'current_bids': current_bids,
        'paddle_raises': paddle_raises,
        'team_stats': team_stats,
        'available_players': available_players,
        'recent_sales': recent_sales,
        'total_teams': teams.count(),
        'search_query': search_query,
    })

@login_required
@user_passes_test(is_auctioneer)
def auctioneer_quick_bid(request):
    """
    Quick bid entry via AJAX - for when team owner paddles
    
    This is now the ONLY way to place bids in the system.
    Team owners cannot bid directly anymore.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    team_id = request.POST.get('team_id')
    player_id = request.POST.get('player_id')
    amount = request.POST.get('amount')
    
    if not all([team_id, player_id, amount]):
        return JsonResponse({'success': False, 'message': 'Missing required fields'})
    
    try:
        from django.db import transaction
        
        with transaction.atomic():
            team = Team.objects.select_for_update().get(id=team_id)
            player = Player.objects.select_for_update().get(id=player_id)
            session = AuctionSession.objects.select_for_update().filter(status='live').first()
            
            if not session:
                return JsonResponse({'success': False, 'message': 'No active auction session'})
            
            if not session.current_player or session.current_player_id != int(player_id):
                return JsonResponse({'success': False, 'message': 'This player is not currently being auctioned'})
            
            amount = int(amount)
            
            # Validation
            if not team.can_buy_player():
                return JsonResponse({
                    'success': False, 
                    'message': f'{team.name} has reached maximum player limit'
                })
            
            if team.purse_remaining < amount:
                return JsonResponse({
                    'success': False, 
                    'message': f'{team.name} has insufficient purse (₹{team.purse_remaining} remaining)'
                })
            
            # Check bid increment
            if player.current_bid == 0:
                if amount != player.base_price:
                    return JsonResponse({
                        'success': False, 
                        'message': f'First bid must be base price: ₹{player.base_price}'
                    })
            else:
                increment = 50 if player.current_bid < 700 else 100
                expected_bid = player.current_bid + increment
                
                if amount != expected_bid:
                    return JsonResponse({
                        'success': False, 
                        'message': f'Next bid must be: ₹{expected_bid}'
                    })
            
            # Create bid
            bid = Bid.objects.create(
                auction_session=session,
                player=player,
                team=team,
                amount=amount
            )
            
            # Update player and session
            player.current_bid = amount
            player.save()
            
            session.last_bid_team = team
            session.bid_call_count = 0  # Reset going count
            session.save()
            
            # Calculate next bid
            next_increment = 50 if amount < 700 else 100
            next_bid = amount + next_increment
            
            # Check which teams can still bid
            can_bid_teams = []
            for t in Team.objects.all():
                if t.can_buy_player() and t.purse_remaining >= next_bid:
                    can_bid_teams.append(t.id)
            
            bid_data = {
                'success': True,
                'bid_id': bid.id,
                'team_name': team.name,
                'team_id': team.id,
                'player_id': player.id,
                'player_name': player.user.get_full_name(),
                'amount': amount,
                'next_bid': next_bid,
                'purse_remaining': team.purse_remaining,
                'team_slots_remaining': team.slots_remaining(),
                'can_bid_teams': can_bid_teams,
                'timestamp': bid.timestamp.isoformat(),
            }
            
            # IMPORTANT: Broadcast to all WebSocket clients
            broadcast_bid_update(bid_data)
            
            return JsonResponse(bid_data)
            
    except Team.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Team not found'})
    except Player.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Player not found'})
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid bid amount'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


@login_required
@user_passes_test(is_auctioneer)
def auctioneer_start_player(request):
    """Start bidding for a player - broadcasts to all clients"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    player_id = request.POST.get('player_id')
    
    try:
        from django.db import transaction
        
        with transaction.atomic():
            session = AuctionSession.objects.select_for_update().filter(status='live').first()
            if not session:
                return JsonResponse({'success': False, 'message': 'No active session'})
            
            player = Player.objects.select_for_update().get(id=player_id, status='approved')
            
            # Reset player
            player.current_bid = 0
            player.save()
            
            session.current_player = player
            session.last_bid_team = None
            session.bid_call_count = 0
            session.save()
            
            player_data = {
                'success': True,
                'player': {
                    'id': player.id,
                    'name': player.user.get_full_name(),
                    'category': player.get_category_display(),
                    'base_price': player.base_price,
                    'current_bid': 0,
                    'next_bid': player.base_price,
                    'photo': player.user.profile_picture.url if player.user.profile_picture else None,
                }
            }
            
            # Broadcast to all WebSocket clients
            broadcast_player_update(player_data)
            
            return JsonResponse(player_data)
            
    except Player.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Player not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_auctioneer)
def auctioneer_complete_sale(request):
    """
    Mark player as sold/unsold - broadcasts to all clients
    
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    player_id = request.POST.get('player_id')
    
    try:
        from django.db import transaction
        from .models import AuctionLog
        
        with transaction.atomic():
            session = AuctionSession.objects.select_for_update().filter(status='live').first()
            if not session:
                return JsonResponse({'success': False, 'message': 'No active session'})
            if not session.current_player:
                return JsonResponse({
                    'success': False,
                    'message': 'No player currently being auctioned. Please select a player first.'
                })
            player = Player.objects.select_for_update().get(id=player_id)
            
            # CRITICAL FIX: Check if player is already sold/unsold
            if player.status in ['sold', 'unsold']:
                return JsonResponse({
                    'success': False, 
                    'message': f'Player already {player.status}! Cannot process again.',
                    'already_processed': True
                })
            
            # ADDITIONAL CHECK: Verify this is the current player
            if not session.current_player or session.current_player.id != player.id:
                return JsonResponse({
                    'success': False,
                    'message': 'This player is not currently being auctioned'
                })
            
            winning_bid = Bid.objects.filter(
                player=player,
                auction_session=session
            ).order_by('-amount').first()
            
            if winning_bid:
                # Player SOLD
                team = Team.objects.select_for_update().get(id=winning_bid.team_id)
                
                # Check team can still buy
                if not team.can_buy_player():
                    return JsonResponse({
                        'success': False,
                        'message': f'{team.name} has reached maximum player limit'
                    })
                
                # Check team still has enough purse
                if team.purse_remaining < winning_bid.amount:
                    return JsonResponse({
                        'success': False,
                        'message': f'{team.name} no longer has enough purse (someone else may have bought players)'
                    })
                
                # Mark player as SOLD
                player.status = 'sold'
                player.team = team
                player.save()
                
                # Deduct from team purse
                team.purse_remaining -= winning_bid.amount
                team.save()
                
                # Create auction log
                AuctionLog.objects.create(
                    auction_session=session,
                    player=player,
                    winning_team=team,
                    final_amount=winning_bid.amount,
                    sold=True
                )
                
                # Clear current player from session
                session.current_player = None
                session.last_bid_team = None
                session.bid_call_count = 0
                session.save()
                
                result_data = {
                    'success': True,
                    'sold': True,
                    'team_name': team.name,
                    'team_id': team.id,
                    'amount': winning_bid.amount,
                    'player_name': player.user.get_full_name(),
                    'player_id': player.id,
                    'team_purse_remaining': team.purse_remaining,
                }
                
                # Broadcast to all WebSocket clients
                broadcast_bidding_end(result_data)
                
                return JsonResponse(result_data)
            else:
                # Player UNSOLD
                player.status = 'unsold'
                player.save()
                
                # Create auction log
                AuctionLog.objects.create(
                    auction_session=session,
                    player=player,
                    final_amount=player.base_price,
                    sold=False
                )
                
                # Clear current player from session
                session.current_player = None
                session.last_bid_team = None
                session.bid_call_count = 0
                session.save()
                
                result_data = {
                    'success': True,
                    'sold': False,
                    'player_name': player.user.get_full_name(),
                    'player_id': player.id,
                }
                
                # Broadcast to all WebSocket clients
                broadcast_bidding_end(result_data)
                
                return JsonResponse(result_data)
                
    except Player.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Player not found'})
    except Team.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Team not found'})
    except Exception as e:
        import traceback
        print(f"Error in complete_sale: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

@login_required
@user_passes_test(is_auctioneer)
def auctioneer_call_going(request):
    """Increment 'Going once, twice, sold' counter"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    try:
        session = AuctionSession.objects.filter(status='live').first()
        if not session:
            return JsonResponse({'success': False, 'message': 'No active session'})
        
        session.bid_call_count += 1
        session.save()
        
        call_text = ['Going once...', 'Going twice...', 'SOLD!'][min(session.bid_call_count - 1, 2)]
        
        return JsonResponse({
            'success': True,
            'call_count': session.bid_call_count,
            'call_text': call_text,
            'should_complete': session.bid_call_count >= 3
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_auctioneer)
def auctioneer_team_info(request, team_id):
    """Get detailed team info via AJAX"""
    try:
        team = Team.objects.prefetch_related('players__user').get(id=team_id)
        players = team.players.all()
        
        player_list = [{
            'name': p.user.get_full_name(),
            'category': p.get_category_display(),
            'price': p.current_bid or p.base_price,
        } for p in players]
        
        return JsonResponse({
            'success': True,
            'team': {
                'name': team.name,
                'owner': team.owner.get_full_name(),
                'purse_remaining': team.purse_remaining,
                'purse_spent': team.purse_spent(),
                'total_purse': team.total_purse,
                'players_count': players.count(),
                'max_players': team.max_players,
                'slots_remaining': team.slots_remaining(),
                'players': player_list,
            }
        })
    except Team.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Team not found'})
    
@login_required
@user_passes_test(is_admin)
def manage_banners(request):
    """Admin page to manage tournament banners"""
    
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            position = request.POST.get('position')
            image = request.FILES.get('image')
            heading = request.POST.get('heading', '')
            subheading = request.POST.get('subheading', '')
            description = request.POST.get('description', '')
            button_text = request.POST.get('button_text', '')
            button_link = request.POST.get('button_link', '')
            order = int(request.POST.get('order', 0))
            is_active = request.POST.get('is_active') == 'on'
            
            banner = TournamentBanner.objects.create(
                title=title,
                position=position,
                image=image,
                heading=heading,
                subheading=subheading,
                description=description,
                button_text=button_text,
                button_link=button_link,
                order=order,
                is_active=is_active
            )
            
            messages.success(request, f'Banner "{title}" created successfully!')
            return redirect('manage_banners')
            
        except Exception as e:
            messages.error(request, f'Error creating banner: {str(e)}')
    
    # Get banners by position
    hero_banners = TournamentBanner.objects.filter(position='hero').order_by('order')
    secondary_banners = TournamentBanner.objects.filter(position='secondary').order_by('order')
    footer_banners = TournamentBanner.objects.filter(position='footer').order_by('order')
    
    context = {
        'hero_banners': hero_banners,
        'secondary_banners': secondary_banners,
        'footer_banners': footer_banners,
    }
    return render(request, 'admin/manage_banners.html', context)


@login_required
@user_passes_test(is_admin)
def edit_banner(request, banner_id):
    """Edit existing banner"""
    banner = get_object_or_404(TournamentBanner, id=banner_id)
    
    if request.method == 'POST':
        try:
            banner.title = request.POST.get('title')
            banner.position = request.POST.get('position')
            banner.heading = request.POST.get('heading', '')
            banner.subheading = request.POST.get('subheading', '')
            banner.description = request.POST.get('description', '')
            banner.button_text = request.POST.get('button_text', '')
            banner.button_link = request.POST.get('button_link', '')
            banner.order = int(request.POST.get('order', 0))
            banner.is_active = request.POST.get('is_active') == 'on'
            
            # Only update image if new one is uploaded
            if request.FILES.get('image'):
                banner.image = request.FILES.get('image')
            
            banner.save()
            
            messages.success(request, f'Banner "{banner.title}" updated successfully!')
            return redirect('manage_banners')
            
        except Exception as e:
            messages.error(request, f'Error updating banner: {str(e)}')
    
    context = {
        'banner': banner,
    }
    return render(request, 'admin/edit_banner.html', context)


@login_required
@user_passes_test(is_admin)
def delete_banner(request, banner_id):
    """Delete banner via AJAX"""
    if request.method == 'POST':
        try:
            banner = get_object_or_404(TournamentBanner, id=banner_id)
            title = banner.title
            banner.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Banner "{title}" deleted successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@user_passes_test(is_admin)
def toggle_banner(request, banner_id):
    """Toggle banner active status via AJAX"""
    if request.method == 'POST':
        try:
            banner = get_object_or_404(TournamentBanner, id=banner_id)
            data = json.loads(request.body)
            banner.is_active = data.get('is_active', False)
            banner.save()
            
            status = 'activated' if banner.is_active else 'deactivated'
            return JsonResponse({
                'success': True,
                'message': f'Banner "{banner.title}" {status}!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@user_passes_test(is_admin)
def reorder_banners(request):
    """Reorder banners via AJAX drag-and-drop"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            banner_order = data.get('order', [])
            
            for index, banner_id in enumerate(banner_order):
                TournamentBanner.objects.filter(id=banner_id).update(order=index)
            
            return JsonResponse({
                'success': True,
                'message': 'Banners reordered successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# ============================================================================
# PUBLIC TEAM VIEWS
# ============================================================================

def team_list(request):
    """Public view - List all teams"""
    teams = Team.objects.annotate(
        player_count=Count('players'),
        total_spent=Sum('players__current_bid')
    ).select_related('owner').order_by('name')
    
    context = {
        'teams': teams,
        'total_teams': teams.count(),
    }
    return render(request, 'teams/team_list.html', context)


def team_detail(request, team_id):
    """Public view - Team details with players"""
    team = get_object_or_404(Team, id=team_id)
    
    players = team.players.filter(status='sold').select_related('user').order_by('-current_bid')
    
    # Squad composition
    squad_composition = {
        'batsman': players.filter(category='batsman'),
        'bowler': players.filter(category='bowler'),
        'all_rounder': players.filter(category='all_rounder'),
        'wicket_keeper': players.filter(category='wicket_keeper'),
    }
    
    # Statistics
    total_spent = sum(p.current_bid for p in players)
    avg_player_cost = total_spent / players.count() if players.count() > 0 else 0
    most_expensive = players.first() if players.exists() else None
    
    context = {
        'team': team,
        'players': players,
        'squad_composition': squad_composition,
        'total_spent': total_spent,
        'avg_player_cost': avg_player_cost,
        'most_expensive': most_expensive,
        'purse_spent_percentage': (total_spent / team.total_purse * 100) if team.total_purse else 0,
    }
    return render(request, 'teams/team_detail.html', context)


# ============================================================================
# TEAM OWNER VIEWS
# ============================================================================

@login_required
@user_passes_test(is_team_owner)
def my_team(request):
    """Team owner's team management page - UPDATED to show iconic players"""
    try:
        team = request.user.owned_team
    except Team.DoesNotExist:
        return render(request, 'owner/no_team.html')
    
    # Separate regular and iconic players
    all_players = team.players.filter(status='sold').select_related('user').order_by('-current_bid')
    iconic_players = all_players.filter(user__player_type='faculty')
    regular_players = all_players.exclude(user__player_type='faculty')
    
    # Calculate effective squad size
    iconic_count = iconic_players.count()
    effective_max_players = team.max_players - iconic_count
    regular_count = regular_players.count()
    
    # Squad composition (regular players only)
    squad_stats = {
        'batsman': {
            'count': regular_players.filter(category='batsman').count(),
            'players': regular_players.filter(category='batsman'),
            'spent': sum(p.current_bid for p in regular_players.filter(category='batsman'))
        },
        'bowler': {
            'count': regular_players.filter(category='bowler').count(),
            'players': regular_players.filter(category='bowler'),
            'spent': sum(p.current_bid for p in regular_players.filter(category='bowler'))
        },
        'all_rounder': {
            'count': regular_players.filter(category='all_rounder').count(),
            'players': regular_players.filter(category='all_rounder'),
            'spent': sum(p.current_bid for p in regular_players.filter(category='all_rounder'))
        },
        'wicket_keeper': {
            'count': regular_players.filter(category='wicket_keeper').count(),
            'players': regular_players.filter(category='wicket_keeper'),
            'spent': sum(p.current_bid for p in regular_players.filter(category='wicket_keeper'))
        },
    }
    
    # Recent auction activity
    recent_bids = Bid.objects.filter(team=team).select_related('player__user').order_by('-timestamp')[:10]
    
    # Auction wins
    auction_wins = AuctionLog.objects.filter(
        winning_team=team,
        sold=True
    ).select_related('player__user').order_by('-timestamp')
    
    context = {
        'team': team,
        'players': regular_players,
        'iconic_players': iconic_players,
        'iconic_count': iconic_count,
        'regular_count': regular_count,
        'effective_max_players': effective_max_players,
        'squad_stats': squad_stats,
        'recent_bids': recent_bids,
        'auction_wins': auction_wins,
        'total_spent': team.purse_spent(),
        'purse_percentage': (team.purse_remaining / team.total_purse * 100) if team.total_purse else 0,
    }
    return render(request, 'owner/my_team.html', context)

    """Team owner's team management page"""
    try:
        team = request.user.owned_team
    except Team.DoesNotExist:
        return render(request, 'owner/no_team.html')
    
    players = team.players.filter(status='sold').select_related('user').order_by('-current_bid')
    
    # Detailed squad analysis
    squad_stats = {
        'batsman': {
            'count': players.filter(category='batsman').count(),
            'players': players.filter(category='batsman'),
            'spent': sum(p.current_bid for p in players.filter(category='batsman'))
        },
        'bowler': {
            'count': players.filter(category='bowler').count(),
            'players': players.filter(category='bowler'),
            'spent': sum(p.current_bid for p in players.filter(category='bowler'))
        },
        'all_rounder': {
            'count': players.filter(category='all_rounder').count(),
            'players': players.filter(category='all_rounder'),
            'spent': sum(p.current_bid for p in players.filter(category='all_rounder'))
        },
        'wicket_keeper': {
            'count': players.filter(category='wicket_keeper').count(),
            'players': players.filter(category='wicket_keeper'),
            'spent': sum(p.current_bid for p in players.filter(category='wicket_keeper'))
        },
    }
    
    # Recent auction activity
    recent_bids = Bid.objects.filter(team=team).select_related('player__user').order_by('-timestamp')[:10]
    
    # Auction logs for this team
    auction_wins = AuctionLog.objects.filter(
        winning_team=team,
        sold=True
    ).select_related('player__user').order_by('-timestamp')
    
    context = {
        'team': team,
        'players': players,
        'squad_stats': squad_stats,
        'recent_bids': recent_bids,
        'auction_wins': auction_wins,
        'total_spent': team.purse_spent(),
        'purse_percentage': (team.purse_remaining / team.total_purse * 100) if team.total_purse else 0,
    }
    return render(request, 'owner/my_team.html', context)


@login_required
@user_passes_test(is_team_owner)
def player_profile(request, player_id):
    """Detailed player profile view for team owner"""
    player = get_object_or_404(Player, id=player_id)
    
    # Check if this player belongs to the owner's team
    try:
        team = request.user.owned_team
        if player.team != team:
            messages.warning(request, 'This player is not in your team!')
            return redirect('my_team')
    except Team.DoesNotExist:
        return redirect('owner_dashboard')
    
    # Player's bidding history
    bid_history = Bid.objects.filter(player=player).select_related('team').order_by('-timestamp')
    
    context = {
        'player': player,
        'bid_history': bid_history,
        'team': team,
    }
    return render(request, 'owner/player_profile.html', context)


# ============================================================================
# ADMIN TEAM MANAGEMENT VIEWS
# ============================================================================

@login_required
@user_passes_test(is_admin)
def admin_team_overview(request):
    """Admin view - Comprehensive team management"""
    teams = Team.objects.annotate(
        player_count=Count('players'),
        total_spent=Sum('players__current_bid')
    ).select_related('owner', 'manager').order_by('name')
    
    # Overall statistics
    total_purse_distributed = sum(t.total_purse for t in teams)
    total_purse_spent = sum(t.purse_spent() for t in teams)
    total_players_sold = Player.objects.filter(status='sold').count()
    
    # Team with most/least spending
    team_spending = [(t, t.purse_spent()) for t in teams]
    most_spending_team = max(team_spending, key=lambda x: x[1]) if team_spending else (None, 0)
    least_spending_team = min(team_spending, key=lambda x: x[1]) if team_spending else (None, 0)
    
    context = {
        'teams': teams,
        'total_teams': teams.count(),
        'total_purse_distributed': total_purse_distributed,
        'total_purse_spent': total_purse_spent,
        'total_players_sold': total_players_sold,
        'most_spending_team': most_spending_team,
        'least_spending_team': least_spending_team,
    }
    return render(request, 'admin/team_overview.html', context)


@login_required
@user_passes_test(is_admin)
def admin_team_detail(request, team_id):
    """Admin view - Detailed team management"""
    team = get_object_or_404(Team, id=team_id)
    
    players = team.players.filter(status='sold').select_related('user').order_by('-current_bid')
    
    # Squad composition
    squad_composition = {
        'batsman': players.filter(category='batsman'),
        'bowler': players.filter(category='bowler'),
        'all_rounder': players.filter(category='all_rounder'),
        'wicket_keeper': players.filter(category='wicket_keeper'),
    }
    
    # Auction activity
    all_bids = Bid.objects.filter(team=team).select_related('player__user').order_by('-timestamp')[:20]
    auction_wins = AuctionLog.objects.filter(winning_team=team, sold=True).select_related('player__user')
    
    # Team finances
    total_spent = team.purse_spent()
    avg_player_cost = total_spent / players.count() if players.count() > 0 else 0
    
    context = {
        'team': team,
        'players': players,
        'squad_composition': squad_composition,
        'all_bids': all_bids,
        'auction_wins': auction_wins,
        'total_spent': total_spent,
        'avg_player_cost': avg_player_cost,
    }
    return render(request, 'admin/team_detail.html', context)


@login_required
@user_passes_test(is_admin)
def admin_edit_team(request, team_id):
    """Admin edit team details"""
    team = get_object_or_404(Team, id=team_id)
    
    if request.method == 'POST':
        team.name = request.POST.get('name')
        team.total_purse = int(request.POST.get('total_purse', team.total_purse))
        team.max_players = int(request.POST.get('max_players', team.max_players))
        
        # Update owner if changed
        owner_id = request.POST.get('owner')
        if owner_id:
            new_owner = User.objects.get(id=owner_id, user_type='team_owner')
            team.owner = new_owner
        
        # Update manager if provided
        manager_id = request.POST.get('manager')
        if manager_id:
            team.manager = User.objects.get(id=manager_id, user_type='team_manager')
        else:
            team.manager = None
        
        # Update logo if provided
        if request.FILES.get('logo'):
            team.logo = request.FILES.get('logo')
        
        team.save()
        messages.success(request, f'Team "{team.name}" updated successfully!')
        return redirect('admin_team_detail', team_id=team.id)
    
    # Get available owners and managers
    available_owners = User.objects.filter(user_type='team_owner')
    available_managers = User.objects.filter(user_type='team_manager')
    
    context = {
        'team': team,
        'available_owners': available_owners,
        'available_managers': available_managers,
    }
    return render(request, 'admin/edit_team.html', context)


@login_required
@user_passes_test(is_admin)
def admin_delete_team(request, team_id):
    """Admin delete team (with confirmation)"""
    if request.method == 'POST':
        team = get_object_or_404(Team, id=team_id)
        team_name = team.name
        
        # Reset all players from this team
        team.players.all().update(team=None, status='approved', current_bid=0)
        
        # Delete team
        team.delete()
        
        messages.success(request, f'Team "{team_name}" deleted successfully! All players have been reset.')
        return redirect('admin_team_overview')
    
    return redirect('admin_team_overview')


@login_required
@user_passes_test(is_admin)
def admin_reset_team(request, team_id):
    
    if request.method == 'POST':
        team = get_object_or_404(Team, id=team_id)
        
        with transaction.atomic():
            # Get all players from this team
            players = team.players.all()
            player_count = players.count()
            
            # Reset each player properly
            for player in players:
                #  Only reset regular players to 'approved'
                # Keep iconic players as 'approved' but remove team assignment
                if player.user.player_type == 'faculty':  # Iconic player
                    player.team = None
                    player.status = 'approved'
                    player.current_bid = 0
                else:  # Regular player
                    player.team = None
                    player.status = 'approved'  # Changed from 'sold' to 'approved'
                    player.current_bid = player.base_price  # Reset to base price
                
                player.save()
            
            # Reset purse
            team.purse_remaining = team.total_purse
            team.save()
        
        messages.success(request, f'Team "{team.name}" reset! {player_count} players released (set to approved/unsold) and purse restored to ₹{team.total_purse}.')
        return redirect('admin_team_detail', team_id=team.id)
    
    return redirect('admin_team_overview')


@login_required
@user_passes_test(is_admin)
def admin_remove_player_from_team(request, team_id, player_id):
    """Remove a specific player from a team"""
    if request.method == 'POST':
        team = get_object_or_404(Team, id=team_id)
        player = get_object_or_404(Player, id=player_id, team=team)
        
        # Refund the amount to team
        team.purse_remaining += player.current_bid
        team.save()
        
        # Reset player
        player_name = player.user.get_full_name()
        refund_amount = player.current_bid
        player.team = None
        player.status = 'approved'
        player.current_bid = 0
        player.save()
        
        messages.success(request, f'Player "{player_name}" removed from "{team.name}". ₹{refund_amount} refunded to team purse.')
        return redirect('admin_team_detail', team_id=team.id)
    
    return redirect('admin_team_overview')

# ============================================================================
# ICONIC PLAYER MANAGEMENT (NEW)
# ============================================================================

@login_required
@user_passes_test(is_admin)
def manage_iconic_players(request):
    """Admin page to assign iconic players (faculty) to teams"""
    
    # Get all teams
    teams = Team.objects.all().order_by('name')
    
    # Get all faculty players (iconic players)
    iconic_players = Player.objects.filter(
        user__player_type='faculty',
        status__in=['approved', 'sold']  # Include both available and already assigned
    ).select_related('user', 'team').order_by('user__first_name')
    
    assigned_iconic_players = iconic_players.filter(status='sold')
    available_iconic_players = iconic_players.filter(status='approved')

    # Build team data with their iconic players
    team_data = []
    for team in teams:
        team_iconic = team.players.filter(user__player_type='faculty')
        can_add = team_iconic.count() < 2
        
        team_data.append({
            'team': team,
            'iconic_players': team_iconic,
            'iconic_count': team_iconic.count(),
            'can_add_more': can_add,
        })
    
    context = {
        'team_data': team_data,
        'iconic_players': iconic_players,
        'total_iconic_players': iconic_players.count(),
        'assigned_iconic_count': assigned_iconic_players.count(),
        'available_iconic_count': available_iconic_players.count(),
    }
    return render(request, 'admin/manage_iconic_players.html', context)


@login_required
@user_passes_test(is_admin)
def assign_iconic_player(request):
    """Assign iconic player to a team via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        team_id = request.POST.get('team_id')
        player_id = request.POST.get('player_id')
        
        with transaction.atomic():
            team = Team.objects.select_for_update().get(id=team_id)
            player = Player.objects.select_for_update().get(id=player_id)
            
            # Validation: Check if player is faculty
            if player.user.player_type != 'faculty':
                return JsonResponse({
                    'success': False,
                    'message': 'Only faculty players can be assigned as iconic players'
                })
            
            # Validation: Check team iconic player limit (max 2)
            current_iconic_count = team.players.filter(user__player_type='faculty').count()
            if current_iconic_count >= 2:
                return JsonResponse({
                    'success': False,
                    'message': f'{team.name} already has 2 iconic players (maximum allowed)'
                })
            
            # Validation: Check if player is already assigned to another team
            if player.team and player.team.id != team.id:
                return JsonResponse({
                    'success': False,
                    'message': f'{player.user.get_full_name()} is already assigned to {player.team.name}'
                })
            
            # Check if team has space (considering iconic players reduce squad size)
            max_regular_players = team.max_players - current_iconic_count - 1  # -1 for this new iconic player
            regular_players_count = team.players.exclude(user__player_type='faculty').count()
            
            if regular_players_count > max_regular_players:
                return JsonResponse({
                    'success': False,
                    'message': f'Adding this iconic player would violate squad size limits'
                })
            
            # Assign player to team
            player.team = team
            player.status = 'sold'
            player.current_bid = 0  # Iconic players are free
            player.save()
            
            # Create audit log (not in auction context, but track the assignment)
            active_session = AuctionSession.objects.filter(status='live').first()
            if active_session:
                AuctionLog.objects.create(
                    auction_session=active_session,
                    player=player,
                    winning_team=team,
                    final_amount=0,
                    sold=True
                )
            
            return JsonResponse({
                'success': True,
                'message': f'{player.user.get_full_name()} assigned to {team.name} as iconic player',
                'player_name': player.user.get_full_name(),
                'team_name': team.name,
                'iconic_count': team.players.filter(user__player_type='faculty').count()
            })
            
    except Team.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Team not found'})
    except Player.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Player not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


@login_required
@user_passes_test(is_admin)
def remove_iconic_player(request):
    """Remove iconic player from a team via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        player_id = request.POST.get('player_id')
        
        with transaction.atomic():
            player = Player.objects.select_for_update().get(id=player_id)
            
            if player.user.player_type != 'faculty':
                return JsonResponse({
                    'success': False,
                    'message': 'This is not an iconic player'
                })
            
            team_name = player.team.name if player.team else 'N/A'
            player_name = player.user.get_full_name()
            
            # Remove from team
            player.team = None
            player.status = 'approved'
            player.current_bid = 0
            player.save()
            
            return JsonResponse({
                'success': True,
                'message': f'{player_name} removed from {team_name}',
                'player_name': player_name
            })
            
    except Player.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Player not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


# ============================================================================
# REPORTS & EXPORTS (NEW)
# ============================================================================

@login_required
@user_passes_test(is_admin)
def export_reports(request):
    """Admin page with all available export options"""
    
    # Gather statistics for display
    total_teams = Team.objects.count()
    total_players = Player.objects.count()
    sold_players = Player.objects.filter(status='sold').count()
    iconic_players = Player.objects.filter(user__player_type='faculty', status='sold').count()
    
    total_purse_distributed = sum(t.total_purse for t in Team.objects.all())
    total_purse_spent = sum(t.purse_spent() for t in Team.objects.all())
    
    auction_sessions = AuctionSession.objects.all().order_by('-created_at')
    
    context = {
        'total_teams': total_teams,
        'total_players': total_players,
        'sold_players': sold_players,
        'iconic_players': iconic_players,
        'total_purse_distributed': total_purse_distributed,
        'total_purse_spent': total_purse_spent,
        'auction_sessions': auction_sessions,
    }
    return render(request, 'admin/export_reports.html', context)


@login_required
@user_passes_test(is_admin)
def export_teams_report(request):
    """Export all teams with their players"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="teams_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Team Name', 'Owner', 'Manager', 'Total Purse', 'Purse Remaining', 'Purse Spent', 'Total Players', 'Regular Players', 'Iconic Players', 'Max Players'])
    
    teams = Team.objects.all().select_related('owner', 'manager')
    for team in teams:
        iconic_count = team.players.filter(user__player_type='faculty').count()
        regular_count = team.players.exclude(user__player_type='faculty').count()
        
        writer.writerow([
            team.name,
            team.owner.get_full_name(),
            team.manager.get_full_name() if team.manager else 'N/A',
            team.total_purse,
            team.purse_remaining,
            team.purse_spent(),
            team.players.count(),
            regular_count,
            iconic_count,
            team.max_players
        ])
    
    return response


@login_required
@user_passes_test(is_admin)
def export_players_report(request):
    """Export all players with their details"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="players_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Player Name', 'Player Type', 'Category', 'Status', 'Team', 'Base Price', 'Sale Price', 'Roll Number', 'Course', 'Branch', 'Year', 'Phone', 'Email'])
    
    players = Player.objects.all().select_related('user', 'team')
    for player in players:
        writer.writerow([
            player.user.get_full_name(),
            player.user.get_player_type_display() if player.user.player_type else 'N/A',
            player.get_category_display(),
            player.get_status_display(),
            player.team.name if player.team else 'Unassigned',
            player.base_price,
            player.current_bid if player.status == 'sold' else 0,
            player.user.roll_number or 'N/A',
            player.user.get_course_display() if player.user.course else 'N/A',
            player.user.get_branch_display() if player.user.branch else 'N/A',
            player.user.get_year_of_study_display() if player.user.year_of_study else 'N/A',
            player.user.phone or 'N/A',
            player.user.email
        ])
    
    return response


@login_required
@user_passes_test(is_admin)
def export_auction_logs(request):
    """Export auction logs"""
    session_id = request.GET.get('session_id')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="auction_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Player Name', 'Player Type', 'Category', 'Winning Team', 'Final Amount', 'Sold', 'Timestamp', 'Session'])
    
    logs = AuctionLog.objects.all().select_related('player__user', 'winning_team', 'auction_session')
    if session_id:
        logs = logs.filter(auction_session_id=session_id)
    
    logs = logs.order_by('-timestamp')
    
    for log in logs:
        writer.writerow([
            log.player.user.get_full_name(),
            log.player.user.get_player_type_display() if log.player.user.player_type else 'N/A',
            log.player.get_category_display(),
            log.winning_team.name if log.winning_team else 'N/A',
            log.final_amount,
            'Yes' if log.sold else 'No',
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.auction_session.name
        ])
    
    return response


@login_required
@user_passes_test(is_admin)
def export_team_squads(request):
    """Export detailed team squads"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="team_squads_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Team', 'Player Name', 'Player Type', 'Category', 'Price', 'Batting Style', 'Bowling Style', 'Roll Number', 'Branch'])
    
    teams = Team.objects.all().prefetch_related('players__user')
    for team in teams:
        for player in team.players.all().order_by('-current_bid'):
            is_iconic = player.user.player_type == 'faculty'
            player_type_display = f"{player.user.get_player_type_display()} {'(ICONIC)' if is_iconic else ''}"
            
            writer.writerow([
                team.name,
                player.user.get_full_name(),
                player_type_display,
                player.get_category_display(),
                player.current_bid if not is_iconic else 'FREE (Iconic)',
                player.batting_style or 'N/A',
                player.bowling_style or 'N/A',
                player.user.roll_number or 'N/A',
                player.user.get_branch_display() if player.user.branch else 'N/A'
            ])
    
    return response


def robots_txt(request):
    """Serve robots.txt for search engines"""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /static/admin/",
        "",
        "# Sitemap",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
        "",
        "# Crawl-delay",
        "Crawl-delay: 1",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
