from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.template.loader import render_to_string
import json
from .models import ChatRoom, Message, Customer

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope['user']
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room = ChatRoom.objects.get(name=self.room_name)

        # Verify user belongs to this chat
        if self.user != self.room.customer and self.user != self.room.seller:
            self.close()
            return

        async_to_sync(self.channel_layer.group_add)(
            self.room_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_name,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        message = Message.objects.create(
            room=self.room,
            sender=self.user,
            content=data['message']
        )

        async_to_sync(self.channel_layer.group_send)(
            self.room_name,
            {
                'type': 'chat_message',
                'message': {
                    'content': message.content,
                    'sender': message.sender.username,
                    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
            }
        )

    def chat_message(self, event):
        self.send(text_data=json.dumps(event['message']))