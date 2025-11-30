# auction/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.utils import timezone
from .models import User, Team, Player, AuctionSession, Bid, AuctionLog, TournamentBanner, TournamentContent, TournamentStats, SocialMediaLink, PaddleRaise
from .forms import UserRegistrationForm, PlayerRegistrationForm, TeamCreationForm, AuctionSessionForm, UserProfileEditForm, PlayerProfileEditForm, PlayerDetailsEditForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash





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
    """Auctioneer control center with live auction view"""
    active_session = AuctionSession.objects.filter(status='live').first()
    
    if not active_session:
        # Show auction sessions to start
        sessions = AuctionSession.objects.filter(
            status__in=['upcoming', 'paused']
        ).order_by('-created_at')
        
        return render(request, 'auctioneer/no_auction.html', {
            'sessions': sessions
        })
    
    # Get current player details
    current_player = active_session.current_player
    current_bids = []
    paddle_raises = []
    
    if current_player:
        current_bids = Bid.objects.filter(
            player=current_player,
            auction_session=active_session
        ).select_related('team').order_by('-amount')[:5]
        
        # Get unacknowledged paddle raises
        paddle_raises = PaddleRaise.objects.filter(
            player=current_player,
            auction_session=active_session,
            acknowledged=False
        ).select_related('team').order_by('raised_at')
    
    # Get all teams with quick stats
    teams = Team.objects.annotate(
        player_count=Count('players'),
    ).select_related('owner').order_by('name')
    
    # Add additional stats for each team
    team_stats = []
    for team in teams:
        stats = {
            'team': team,
            'purse_remaining': team.purse_remaining,
            'purse_percentage': (team.purse_remaining / team.total_purse * 100) if team.total_purse > 0 else 0,
            'players_count': team.players.count(),
            'slots_remaining': team.slots_remaining(),
            'can_bid': team.can_buy_player() and team.purse_remaining >= (current_player.current_bid + 50 if current_player and current_player.current_bid < 700 else current_player.current_bid + 100) if current_player else False,
            'last_bid': current_bids.filter(team=team).first() if current_bids else None,
        }
        team_stats.append(stats)
    
    # Get available players
    available_players = Player.objects.filter(
        status='approved'
    ).select_related('user').order_by('base_price')[:20]
    
    # Recent auction logs
    from .models import AuctionLog
    recent_sales = AuctionLog.objects.filter(
        auction_session=active_session
    ).select_related('player__user', 'winning_team').order_by('-timestamp')[:10]
    
    context = {
        'session': active_session,
        'current_player': current_player,
        'current_bids': current_bids,
        'paddle_raises': paddle_raises,
        'team_stats': team_stats,
        'available_players': available_players,
        'recent_sales': recent_sales,
        'total_teams': teams.count(),
    }
    
    return render(request, 'auctioneer/dashboard.html', context)


@login_required
@user_passes_test(is_auctioneer)
def auctioneer_quick_bid(request):
    """Quick bid entry via AJAX - for when team owner paddles"""
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
            
            return JsonResponse({
                'success': True,
                'bid_id': bid.id,
                'team_name': team.name,
                'team_id': team.id,
                'player_id': player.id,
                'amount': amount,
                'next_bid': next_bid,
                'team_purse_remaining': team.purse_remaining,
                'can_bid_teams': can_bid_teams,
                'timestamp': bid.timestamp.isoformat(),
            })
            
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
    """Start bidding for a player"""
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
            
            return JsonResponse({
                'success': True,
                'player': {
                    'id': player.id,
                    'name': player.user.get_full_name(),
                    'category': player.get_category_display(),
                    'base_price': player.base_price,
                    'photo': player.user.profile_picture.url if player.user.profile_picture else None,
                }
            })
            
    except Player.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Player not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_auctioneer)
def auctioneer_complete_sale(request):
    """Mark player as sold/unsold"""
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
            
            player = Player.objects.select_for_update().get(id=player_id)
            
            winning_bid = Bid.objects.filter(
                player=player,
                auction_session=session
            ).order_by('-amount').first()
            
            if winning_bid:
                # Sold
                team = Team.objects.select_for_update().get(id=winning_bid.team_id)
                
                if not team.can_buy_player():
                    return JsonResponse({
                        'success': False,
                        'message': f'{team.name} has reached maximum player limit'
                    })
                
                player.status = 'sold'
                player.team = team
                player.save()
                
                # Update team purse
                team.purse_remaining -= winning_bid.amount
                team.save()
                
                # Log
                AuctionLog.objects.create(
                    auction_session=session,
                    player=player,
                    winning_team=team,
                    final_amount=winning_bid.amount,
                    sold=True
                )
                
                return JsonResponse({
                    'success': True,
                    'sold': True,
                    'team_name': team.name,
                    'amount': winning_bid.amount,
                    'player_name': player.user.get_full_name(),
                })
            else:
                # Unsold
                player.status = 'unsold'
                player.save()
                
                AuctionLog.objects.create(
                    auction_session=session,
                    player=player,
                    final_amount=player.base_price,
                    sold=False
                )
                
                return JsonResponse({
                    'success': True,
                    'sold': False,
                    'player_name': player.user.get_full_name(),
                })
                
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


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