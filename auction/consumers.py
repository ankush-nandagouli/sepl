# # auction/consumers.py
# import json
# import asyncio
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.db import database_sync_to_async
# from django.contrib.auth import get_user_model
# from django.db import transaction
# from django.db.models import F
# from .models import Team, Player, Bid, AuctionSession

# User = get_user_model()

# class AuctionConsumer(AsyncWebsocketConsumer):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.bid_lock = asyncio.Lock()
    
#     async def connect(self):
#         self.room_name = 'auction_room'
#         self.room_group_name = 'auction_room_group'

#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )
#         await self.accept()

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         try:
#             data = json.loads(text_data)
#             action = data.get('action')

#             if action == 'place_bid':
#                 await self.place_bid(data)
#             elif action == 'start_auction':
#                 await self.start_auction(data)
#             elif action == 'next_player':
#                 await self.next_player(data)
#             elif action == 'end_bidding':
#                 await self.end_bidding(data)
#         except json.JSONDecodeError:
#             await self.send(text_data=json.dumps({
#                 'type': 'error',
#                 'message': 'Invalid JSON data'
#             }))
#         except Exception as e:
#             await self.send(text_data=json.dumps({
#                 'type': 'error',
#                 'message': f'Server error: {str(e)}'
#             }))

#     async def place_bid(self, data):
#         # Use lock to prevent concurrent bid processing
#         async with self.bid_lock:
#             team_id = data.get('team_id')
#             player_id = data.get('player_id')
#             amount = data.get('amount')
            
#             # Validate input
#             if not all([team_id, player_id, amount]):
#                 await self.send(text_data=json.dumps({
#                     'type': 'error',
#                     'message': 'Missing required fields'
#                 }))
#                 return
            
#             try:
#                 amount = int(amount)
#             except (ValueError, TypeError):
#                 await self.send(text_data=json.dumps({
#                     'type': 'error',
#                     'message': 'Invalid bid amount'
#                 }))
#                 return
            
#             result = await self.create_bid(team_id, player_id, amount)
            
#             if result['success']:
#                 await self.channel_layer.group_send(
#                     self.room_group_name,
#                     {
#                         'type': 'bid_update',
#                         'data': result
#                     }
#                 )
#             else:
#                 await self.send(text_data=json.dumps({
#                     'type': 'error',
#                     'message': result['message']
#                 }))

#     @database_sync_to_async
#     def create_bid(self, team_id, player_id, amount):
#         try:
#             with transaction.atomic():
#                 # Use select_for_update to lock rows during transaction
#                 team = Team.objects.select_for_update().get(id=team_id)
#                 player = Player.objects.select_for_update().get(id=player_id)
#                 session = AuctionSession.objects.select_for_update().filter(status='live').first()
                
#                 # Validation checks
#                 if not session:
#                     return {'success': False, 'message': 'No active auction session'}
                
#                 if not session.current_player or session.current_player_id != player_id:
#                     return {'success': False, 'message': 'This player is not currently being auctioned'}
                
#                 # Check team player limit (non-admin enforcement)
#                 if not team.can_buy_player():
#                     return {
#                         'success': False, 
#                         'message': f'Team has reached maximum player limit ({team.max_players} players)'
#                     }
                
#                 # Check if team has enough purse
#                 if team.purse_remaining < amount:
#                     return {
#                         'success': False, 
#                         'message': f'Insufficient purse balance. Available: ₹{team.purse_remaining}'
#                     }
                
#                 # Check if bid is valid increment
#                 if player.current_bid == 0:
#                     if amount != player.base_price:
#                         return {
#                             'success': False, 
#                             'message': f'First bid must be base price: ₹{player.base_price}'
#                         }
#                 else:
#                     increment = 50 if player.current_bid < 700 else 100
#                     expected_bid = player.current_bid + increment
                    
#                     if amount != expected_bid:
#                         return {
#                             'success': False, 
#                             'message': f'Invalid bid increment. Next bid must be: ₹{expected_bid}'
#                         }
                
#                 # Create bid
#                 bid = Bid.objects.create(
#                     auction_session=session,
#                     player=player,
#                     team=team,
#                     amount=amount
#                 )
                
#                 # Update player current bid using F() expression to avoid race conditions
#                 Player.objects.filter(id=player_id).update(current_bid=amount)
                
#                 # Reload player to get updated values
#                 player.refresh_from_db()
                
#                 # Calculate next bid amount
#                 next_increment = 50 if amount < 700 else 100
#                 next_bid = amount + next_increment
                
#                 return {
#                     'success': True,
#                     'bid_id': bid.id,
#                     'team_name': team.name,
#                     'team_id': team.id,
#                     'player_id': player.id,
#                     'player_name': player.user.get_full_name(),
#                     'amount': amount,
#                     'next_bid': next_bid,
#                     'purse_remaining': team.purse_remaining,
#                     'team_slots_remaining': team.slots_remaining()
#                 }
                
#         except Team.DoesNotExist:
#             return {'success': False, 'message': 'Team not found'}
#         except Player.DoesNotExist:
#             return {'success': False, 'message': 'Player not found'}
#         except Exception as e:
#             return {'success': False, 'message': f'Error processing bid: {str(e)}'}

#     @database_sync_to_async
#     def start_next_player(self, player_id):
#         try:
#             with transaction.atomic():
#                 session = AuctionSession.objects.select_for_update().filter(status='live').first()
#                 if not session:
#                     return {'success': False, 'message': 'No active auction session'}
                
#                 player = Player.objects.select_for_update().get(id=player_id, status='approved')
                
#                 # Reset current bid
#                 player.current_bid = 0
#                 player.save()
                
#                 session.current_player = player
#                 session.save()
                
#                 # Get player details
#                 user = player.user
#                 player_data = {
#                     'id': player.id,
#                     'name': user.get_full_name(),
#                     'category': player.get_category_display(),
#                     'base_price': player.base_price,
#                     'current_bid': player.current_bid,
#                     'next_bid': player.base_price,
#                     'photo': user.profile_picture.url if user.profile_picture else None,
#                     'batting_style': player.batting_style,
#                     'bowling_style': player.bowling_style,
#                     'previous_team': player.previous_team,
#                 }
                
#                 # Add student/faculty specific details
#                 if user.player_type == 'student':
#                     player_data.update({
#                         'player_type': 'Student',
#                         'roll_number': user.roll_number or 'N/A',
#                         'course': user.get_course_display() if user.course else 'N/A',
#                         'branch': user.get_branch_display() if user.branch else 'N/A',
#                         'year': user.get_year_of_study_display() if user.year_of_study else 'N/A',
#                     })
#                 elif user.player_type == 'faculty':
#                     player_data.update({
#                         'player_type': 'Faculty',
#                         'branch': user.get_branch_display() if user.branch else 'N/A',
#                     })
                
#                 return {
#                     'success': True,
#                     'player': player_data
#                 }
                
#         except Player.DoesNotExist:
#             return {'success': False, 'message': 'Player not found or not approved'}
#         except Exception as e:
#             return {'success': False, 'message': f'Error starting player auction: {str(e)}'}

#     async def next_player(self, data):
#         player_id = data.get('player_id')
        
#         if not player_id:
#             await self.send(text_data=json.dumps({
#                 'type': 'error',
#                 'message': 'Player ID is required'
#             }))
#             return
        
#         result = await self.start_next_player(player_id)
        
#         if result['success']:
#             await self.channel_layer.group_send(
#                 self.room_group_name,
#                 {
#                     'type': 'player_update',
#                     'data': result
#                 }
#             )
#         else:
#             await self.send(text_data=json.dumps({
#                 'type': 'error',
#                 'message': result['message']
#             }))

#     @database_sync_to_async
#     def complete_bidding(self, player_id):
#         try:
#             from .models import AuctionLog
            
#             with transaction.atomic():
#                 session = AuctionSession.objects.select_for_update().filter(status='live').first()
#                 if not session:
#                     return {'success': False, 'message': 'No active auction session'}
                
#                 player = Player.objects.select_for_update().get(id=player_id)
                
#                 winning_bid = Bid.objects.filter(
#                     player=player, 
#                     auction_session=session
#                 ).order_by('-amount').first()
                
#                 if winning_bid:
#                     # Player sold
#                     team = Team.objects.select_for_update().get(id=winning_bid.team_id)
                    
#                     # Final check for team player limit
#                     if not team.can_buy_player():
#                         return {
#                             'success': False,
#                             'message': f'Team {team.name} has reached maximum player limit'
#                         }
                    
#                     player.status = 'sold'
#                     player.team = team
#                     player.save()
                    
#                     # Update team purse using F() expression
#                     Team.objects.filter(id=team.id).update(
#                         purse_remaining=F('purse_remaining') - winning_bid.amount
#                     )
#                     team.refresh_from_db()
                    
#                     # Log the result
#                     AuctionLog.objects.create(
#                         auction_session=session,
#                         player=player,
#                         winning_team=team,
#                         final_amount=winning_bid.amount,
#                         sold=True
#                     )
                    
#                     return {
#                         'success': True,
#                         'sold': True,
#                         'team_name': team.name,
#                         'team_id': team.id,
#                         'amount': winning_bid.amount,
#                         'player_name': player.user.get_full_name(),
#                         'player_id': player.id,
#                         'team_purse_remaining': team.purse_remaining,
#                         'team_slots_remaining': team.slots_remaining()
#                     }
#                 else:
#                     # Player unsold
#                     player.status = 'unsold'
#                     player.save()
                    
#                     AuctionLog.objects.create(
#                         auction_session=session,
#                         player=player,
#                         final_amount=player.base_price,
#                         sold=False
#                     )
                    
#                     return {
#                         'success': True,
#                         'sold': False,
#                         'player_name': player.user.get_full_name(),
#                         'player_id': player.id
#                     }
                    
#         except Player.DoesNotExist:
#             return {'success': False, 'message': 'Player not found'}
#         except Exception as e:
#             return {'success': False, 'message': f'Error completing bidding: {str(e)}'}

#     async def end_bidding(self, data):
#         player_id = data.get('player_id')
        
#         if not player_id:
#             await self.send(text_data=json.dumps({
#                 'type': 'error',
#                 'message': 'Player ID is required'
#             }))
#             return
        
#         result = await self.complete_bidding(player_id)
        
#         if result['success']:
#             await self.channel_layer.group_send(
#                 self.room_group_name,
#                 {
#                     'type': 'bidding_end',
#                     'data': result
#                 }
#             )
#         else:
#             await self.send(text_data=json.dumps({
#                 'type': 'error',
#                 'message': result['message']
#             }))

#     async def bid_update(self, event):
#         await self.send(text_data=json.dumps({
#             'type': 'bid_update',
#             'data': event['data']
#         }))

#     async def player_update(self, event):
#         await self.send(text_data=json.dumps({
#             'type': 'player_update',
#             'data': event['data']
#         }))

#     async def bidding_end(self, event):
#         await self.send(text_data=json.dumps({
#             'type': 'bidding_end',
#             'data': event['data']
#         }))



# auction/consumers.py - UPDATED WITH DISABLED OWNER BIDDING

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.core.cache import cache
from .models import Team, Player, Bid, AuctionSession
import time

User = get_user_model()

class AuctionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for auction updates
    
    IMPORTANT: Team owners can NO LONGER place bids directly.
    This consumer is now READ-ONLY for team owners.
    Only the auctioneer can place bids via the auctioneer dashboard.
    
    Team owners use this only to receive real-time updates.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bid_lock = asyncio.Lock()
    
    async def connect(self):
        self.room_name = 'auction_room'
        self.room_group_name = 'auction_room_group'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages
        
        DEPRECATED: 'place_bid' action is now disabled for team owners.
        Bids must be placed by auctioneer via the auctioneer dashboard.
        """
        try:
            data = json.loads(text_data)
            action = data.get('action')

            # DISABLED: Team owner bidding
            if action == 'place_bid':
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Direct bidding is disabled. The auctioneer will enter all bids during the live auction. Please raise your paddle to signal the auctioneer.'
                }))
                return
            
            # Admin/Auctioneer actions (kept for backward compatibility)
            elif action == 'start_auction':
                await self.start_auction(data)
            elif action == 'next_player':
                await self.next_player(data)
            elif action == 'end_bidding':
                await self.end_bidding(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Unknown action'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON data'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Server error: {str(e)}'
            }))

    # ============================================================
    # DEPRECATED FUNCTION - KEPT FOR REFERENCE ONLY
    # ============================================================
    async def place_bid(self, data):
        """
        DEPRECATED: This function is no longer used.
        
        All bidding is now done by the auctioneer via the auctioneer dashboard.
        Team owners can only view the auction in real-time.
        
        To re-enable team owner bidding, uncomment this function and
        remove the error message in the receive() method.
        """
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': 'Direct bidding is disabled. Please raise your paddle to signal the auctioneer.'
        }))
        return
        
        # COMMENTED OUT - Original bidding logic
        """
        async with self.bid_lock:
            team_id = data.get('team_id')
            player_id = data.get('player_id')
            amount = data.get('amount')
            request_id = data.get('request_id')
            
            if not all([team_id, player_id, amount]):
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Missing required fields'
                }))
                return
            
            try:
                amount = int(amount)
            except (ValueError, TypeError):
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Invalid bid amount'
                }))
                return
            
            if request_id:
                cache_key = f'bid_request_{request_id}'
                if cache.get(cache_key):
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Duplicate bid request detected'
                    }))
                    return
                cache.set(cache_key, True, 30)
            
            rate_limit_key = f'bid_rate_limit_{team_id}_{player_id}'
            last_bid_time = cache.get(rate_limit_key)
            current_time = time.time()
            
            if last_bid_time and (current_time - last_bid_time) < 1:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Please wait before placing another bid'
                }))
                return
            
            cache.set(rate_limit_key, current_time, 5)
            
            result = await self.create_bid(team_id, player_id, amount)
            
            if result['success']:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'bid_update',
                        'data': result
                    }
                )
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': result['message']
                }))
        """

    # ============================================================
    # DEPRECATED FUNCTION - KEPT FOR REFERENCE ONLY
    # ============================================================
    @database_sync_to_async
    def create_bid(self, team_id, player_id, amount):
        """
        DEPRECATED: This function is no longer used by team owners.
        
        Bids are now created only by the auctioneer via:
        views.auctioneer_quick_bid()
        
        This function is kept for reference and potential future use.
        """
        return {
            'success': False,
            'message': 'Direct bidding is disabled. Please raise your paddle to signal the auctioneer.'
        }
        
        # COMMENTED OUT - Original bid creation logic
        """
        try:
            with transaction.atomic():
                try:
                    team = Team.objects.select_for_update(nowait=True).get(id=team_id)
                    player = Player.objects.select_for_update(nowait=True).get(id=player_id)
                    session = AuctionSession.objects.select_for_update(nowait=True).filter(status='live').first()
                except Exception as e:
                    return {'success': False, 'message': 'Another bid is being processed, please try again'}
                
                if not session:
                    return {'success': False, 'message': 'No active auction session'}
                
                if not session.current_player or session.current_player_id != player_id:
                    return {'success': False, 'message': 'This player is not currently being auctioned'}
                
                if not team.owner.is_active:
                    return {'success': False, 'message': 'Your account has been suspended'}
                
                if not team.can_buy_player():
                    return {
                        'success': False, 
                        'message': f'Team has reached maximum player limit ({team.max_players} players)'
                    }
                
                if team.purse_remaining < amount:
                    return {
                        'success': False, 
                        'message': f'Insufficient purse balance. Available: ₹{team.purse_remaining}'
                    }
                
                current_bid = Player.objects.filter(id=player_id).values_list('current_bid', flat=True).first()
                
                if current_bid == 0:
                    if amount != player.base_price:
                        return {
                            'success': False, 
                            'message': f'First bid must be base price: ₹{player.base_price}'
                        }
                else:
                    increment = 50 if current_bid < 700 else 100
                    expected_bid = current_bid + increment
                    
                    if amount != expected_bid:
                        return {
                            'success': False, 
                            'message': f'Invalid bid increment. Next bid must be: ₹{expected_bid}'
                        }
                
                recent_duplicate = Bid.objects.filter(
                    player=player,
                    team=team,
                    amount=amount,
                    auction_session=session
                ).exists()
                
                if recent_duplicate:
                    return {
                        'success': False,
                        'message': 'Duplicate bid detected'
                    }
                
                bid = Bid.objects.create(
                    auction_session=session,
                    player=player,
                    team=team,
                    amount=amount
                )
                
                Player.objects.filter(id=player_id).update(current_bid=amount)
                
                player.refresh_from_db()
                team.refresh_from_db()
                
                next_increment = 50 if amount < 700 else 100
                next_bid = amount + next_increment
                
                return {
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
                    'timestamp': bid.timestamp.isoformat()
                }
                
        except Team.DoesNotExist:
            return {'success': False, 'message': 'Team not found'}
        except Player.DoesNotExist:
            return {'success': False, 'message': 'Player not found'}
        except Exception as e:
            return {'success': False, 'message': f'Error processing bid: {str(e)}'}
        """

    # ============================================================
    # ACTIVE FUNCTIONS - Used for admin/auctioneer control
    # ============================================================

    @database_sync_to_async
    def start_next_player(self, player_id):
        """Admin/Auctioneer function to start a new player"""
        try:
            with transaction.atomic():
                session = AuctionSession.objects.select_for_update().filter(status='live').first()
                if not session:
                    return {'success': False, 'message': 'No active auction session'}
                
                player = Player.objects.select_for_update().get(id=player_id, status='approved')
                
                player.current_bid = 0
                player.save()
                
                session.current_player = player
                session.save()
                
                user = player.user
                player_data = {
                    'id': player.id,
                    'name': user.get_full_name(),
                    'category': player.get_category_display(),
                    'base_price': player.base_price,
                    'current_bid': player.current_bid,
                    'next_bid': player.base_price,
                    'photo': user.profile_picture.url if user.profile_picture else None,
                    'batting_style': player.batting_style,
                    'bowling_style': player.bowling_style,
                    'previous_team': player.previous_team,
                }
                
                if user.player_type == 'student':
                    player_data.update({
                        'player_type': 'Student',
                        'roll_number': user.roll_number or 'N/A',
                        'course': user.get_course_display() if user.course else 'N/A',
                        'branch': user.get_branch_display() if user.branch else 'N/A',
                        'year': user.get_year_of_study_display() if user.year_of_study else 'N/A',
                    })
                elif user.player_type == 'faculty':
                    player_data.update({
                        'player_type': 'Faculty',
                        'branch': user.get_branch_display() if user.branch else 'N/A',
                    })
                
                return {
                    'success': True,
                    'player': player_data
                }
                
        except Player.DoesNotExist:
            return {'success': False, 'message': 'Player not found or not approved'}
        except Exception as e:
            return {'success': False, 'message': f'Error starting player auction: {str(e)}'}

    async def next_player(self, data):
        """Handle next player request"""
        player_id = data.get('player_id')
        
        if not player_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Player ID is required'
            }))
            return
        
        result = await self.start_next_player(player_id)
        
        if result['success']:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_update',
                    'data': result
                }
            )
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': result['message']
            }))

    @database_sync_to_async
    def complete_bidding(self, player_id):
        """Complete bidding for current player"""
        try:
            from .models import AuctionLog
            
            with transaction.atomic():
                session = AuctionSession.objects.select_for_update().filter(status='live').first()
                if not session:
                    return {'success': False, 'message': 'No active auction session'}
                
                player = Player.objects.select_for_update().get(id=player_id)
                
                winning_bid = Bid.objects.filter(
                    player=player, 
                    auction_session=session
                ).order_by('-amount').first()
                
                if winning_bid:
                    team = Team.objects.select_for_update().get(id=winning_bid.team_id)
                    
                    if not team.can_buy_player():
                        return {
                            'success': False,
                            'message': f'Team {team.name} has reached maximum player limit'
                        }
                    
                    player.status = 'sold'
                    player.team = team
                    player.save()
                    
                    Team.objects.filter(id=team.id).update(
                        purse_remaining=F('purse_remaining') - winning_bid.amount
                    )
                    team.refresh_from_db()
                    
                    AuctionLog.objects.create(
                        auction_session=session,
                        player=player,
                        winning_team=team,
                        final_amount=winning_bid.amount,
                        sold=True
                    )
                    
                    return {
                        'success': True,
                        'sold': True,
                        'team_name': team.name,
                        'team_id': team.id,
                        'amount': winning_bid.amount,
                        'player_name': player.user.get_full_name(),
                        'player_id': player.id,
                        'team_purse_remaining': team.purse_remaining,
                        'team_slots_remaining': team.slots_remaining()
                    }
                else:
                    player.status = 'unsold'
                    player.save()
                    
                    AuctionLog.objects.create(
                        auction_session=session,
                        player=player,
                        final_amount=player.base_price,
                        sold=False
                    )
                    
                    return {
                        'success': True,
                        'sold': False,
                        'player_name': player.user.get_full_name(),
                        'player_id': player.id
                    }
                    
        except Player.DoesNotExist:
            return {'success': False, 'message': 'Player not found'}
        except Exception as e:
            return {'success': False, 'message': f'Error completing bidding: {str(e)}'}

    async def end_bidding(self, data):
        """Handle end bidding request"""
        player_id = data.get('player_id')
        
        if not player_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Player ID is required'
            }))
            return
        
        result = await self.complete_bidding(player_id)
        
        if result['success']:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'bidding_end',
                    'data': result
                }
            )
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': result['message']
            }))

    # ============================================================
    # WebSocket event handlers (broadcast to all clients)
    # ============================================================

    async def bid_update(self, event):
        """Broadcast bid update to all connected clients"""
        await self.send(text_data=json.dumps({
            'type': 'bid_update',
            'data': event['data']
        }))

    async def player_update(self, event):
        """Broadcast player update to all connected clients"""
        await self.send(text_data=json.dumps({
            'type': 'player_update',
            'data': event['data']
        }))

    async def bidding_end(self, event):
        """Broadcast bidding end to all connected clients"""
        await self.send(text_data=json.dumps({
            'type': 'bidding_end',
            'data': event['data']
        }))