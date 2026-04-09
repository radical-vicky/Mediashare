# frontend/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'call_{self.room_name}'
        
        logger.info(f"WebSocket connecting to room: {self.room_name}")
        
        # Check if user is authenticated
        if self.scope['user'].is_anonymous:
            logger.warning("Anonymous user tried to connect")
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"User {self.scope['user'].username} connected to {self.room_group_name}")
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user': self.scope['user'].username,
                'user_id': self.scope['user'].id,
            }
        )
    
    async def disconnect(self, close_code):
        logger.info(f"User {self.scope['user'].username} disconnected from {self.room_group_name}")
        
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user': self.scope['user'].username,
                'user_id': self.scope['user'].id,
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            logger.info(f"Received {message_type} from {self.scope['user'].username}")
            
            # Forward to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': message_type,
                    'data': text_data_json,
                    'from': self.scope['user'].username,
                    'from_id': self.scope['user'].id,
                }
            )
        except Exception as e:
            logger.error(f"Error in receive: {e}")
    
    async def signal(self, event):
        await self.send(text_data=json.dumps({
            'type': 'signal',
            'signal': event['data'].get('signal'),
            'from': event.get('from'),
            'from_id': event.get('from_id'),
        }))
    
    async def ice_candidate(self, event):
        await self.send(text_data=json.dumps({
            'type': 'ice_candidate',
            'candidate': event['data'].get('candidate'),
            'from': event.get('from'),
            'from_id': event.get('from_id'),
        }))
    
    async def call_answered(self, event):
        await self.send(text_data=json.dumps({
            'type': 'call_answered',
            'from': event.get('from'),
        }))
    
    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user': event['user'],
            'user_id': event['user_id'],
        }))
    
    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user'],
            'user_id': event['user_id'],
        }))