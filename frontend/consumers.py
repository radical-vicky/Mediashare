import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import CallSession

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'call_{self.room_name}'
        
        # Check if user is authenticated
        if self.scope['user'].is_anonymous:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify room that user has joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user': self.scope['user'].username,
                'user_id': self.scope['user'].id,
            }
        )
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Notify room that user has left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user': self.scope['user'].username,
                'user_id': self.scope['user'].id,
            }
        )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'signal':
            # Forward WebRTC signaling data to other participants
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'signal_message',
                    'signal': text_data_json['signal'],
                    'from': text_data_json['from'],
                    'from_id': text_data_json['from_id'],
                }
            )
        elif message_type == 'chat':
            # Forward chat message to all participants
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': text_data_json['message'],
                    'from': text_data_json['from'],
                    'from_id': text_data_json['from_id'],
                    'timestamp': text_data_json.get('timestamp', ''),
                }
            )
        elif message_type == 'ice_candidate':
            # Forward ICE candidate
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'ice_candidate',
                    'candidate': text_data_json['candidate'],
                    'from': text_data_json['from'],
                    'from_id': text_data_json['from_id'],
                }
            )
    
    async def signal_message(self, event):
        # Send signaling data to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'signal',
            'signal': event['signal'],
            'from': event['from'],
            'from_id': event['from_id'],
        }))
    
    async def chat_message(self, event):
        # Send chat message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'from': event['from'],
            'from_id': event['from_id'],
            'timestamp': event.get('timestamp', ''),
        }))
    
    async def ice_candidate(self, event):
        # Send ICE candidate to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'ice_candidate',
            'candidate': event['candidate'],
            'from': event['from'],
            'from_id': event['from_id'],
        }))
    
    async def user_joined(self, event):
        # Send user joined notification
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user': event['user'],
            'user_id': event['user_id'],
        }))
    
    async def user_left(self, event):
        # Send user left notification
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user'],
            'user_id': event['user_id'],
        }))