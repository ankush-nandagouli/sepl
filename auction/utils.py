

"""
Utility functions for broadcasting auction events via WebSocket
"""

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def broadcast_bid_update(bid_data):
    """
    Broadcast bid update to all connected WebSocket clients
    
    Usage:
        from auction.utils import broadcast_bid_update
        
        broadcast_bid_update({
            'team_name': team.name,
            'team_id': team.id,
            'player_id': player.id,
            'amount': amount,
            'next_bid': next_bid,
            'timestamp': bid.timestamp.isoformat(),
        })
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'auction_room_group',
        {
            'type': 'bid_update',
            'data': bid_data
        }
    )


def broadcast_player_update(player_data):
    """
    Broadcast player change to all connected WebSocket clients
    
    Usage:
        from auction.utils import broadcast_player_update
        
        broadcast_player_update({
            'player': {
                'id': player.id,
                'name': player.user.get_full_name(),
                'category': player.get_category_display(),
                'base_price': player.base_price,
                # ... etc
            }
        })
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'auction_room_group',
        {
            'type': 'player_update',
            'data': player_data
        }
    )


def broadcast_bidding_end(result_data):
    """
    Broadcast bidding completion to all connected WebSocket clients
    
    Usage:
        from auction.utils import broadcast_bidding_end
        
        broadcast_bidding_end({
            'sold': True,
            'team_name': team.name,
            'player_name': player.user.get_full_name(),
            'amount': final_amount,
        })
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'auction_room_group',
        {
            'type': 'bidding_end',
            'data': result_data
        }
    )