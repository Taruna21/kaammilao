import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ChatRoom, Message
from users.models import User


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id   = self.scope['url_route']['kwargs']['room_id']
        self.room_group = f'chat_{self.room_id}'

        # Join the room group
        await self.channel_layer.group_add(
            self.room_group,
            self.channel_name
        )
        await self.accept()

        # Send last 20 messages when user connects
        messages = await self.get_messages()
        await self.send(text_data=json.dumps({
            'type':     'history',
            'messages': messages
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group,
            self.channel_name
        )

    async def receive(self, text_data):
        """Called when frontend sends a message."""
        data      = json.loads(text_data)
        content   = data.get('message', '').strip()
        sender_id = data.get('sender_id')

        if not content:
            return

        # Save to database
        message = await self.save_message(sender_id, content)

        # Broadcast to everyone in the room
        await self.channel_layer.group_send(
            self.room_group,
            {
                'type':      'chat_message',   # calls chat_message method below
                'message':   content,
                'sender_id': sender_id,
                'sender_phone': message['sender_phone'],
                'timestamp': message['timestamp'],
            }
        )

    async def chat_message(self, event):
        """Sends message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type':         'message',
            'message':      event['message'],
            'sender_id':    event['sender_id'],
            'sender_phone': event['sender_phone'],
            'timestamp':    event['timestamp'],
        }))

    @database_sync_to_async
    def get_messages(self):
        room = ChatRoom.objects.get(id=self.room_id)
        messages = room.messages.select_related('sender').order_by('-timestamp')[:20]
        return [
            {
                'message':      m.content,
                'sender_id':    str(m.sender.id),
                'sender_phone': m.sender.phone,
                'timestamp':    m.timestamp.strftime('%H:%M'),
            }
            for m in reversed(list(messages))
        ]

    @database_sync_to_async
    def save_message(self, sender_id, content):
        room   = ChatRoom.objects.get(id=self.room_id)
        sender = User.objects.get(id=sender_id)
        message = Message.objects.create(
            room    = room,
            sender  = sender,
            content = content
        )
        return {
            'sender_phone': sender.phone,
            'timestamp':    message.timestamp.strftime('%H:%M'),
        }