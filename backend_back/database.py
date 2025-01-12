from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import redis
import json

db = SQLAlchemy()
migrate = Migrate()

try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
except:
    print("Warning: Redis connection failed")
    redis_client = None

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    avatar = db.Column(db.String(20), nullable=False, default='default.jpg')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    host_id = db.Column(db.String(50), nullable=False, default='default')

    # 添加索引以提高查询性能
    __table_args__ = (
        db.Index('idx_username_host', username, host_id),
    )

    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    messages = db.relationship('ChatMessage', backref='author', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar': self.avatar,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'host_id': self.host_id
        }

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    host_id = db.Column(db.String(50), default='default')  # 修改这里

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'date_posted': self.date_posted.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': self.user_id,
            'host_id': self.host_id,
            'username': self.author.username
        }

# 添加聊天室成员关联表
chatroom_members = db.Table('chatroom_members',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('room_id', db.Integer, db.ForeignKey('chatrooms.id'), primary_key=True)
)

class ChatRoom(db.Model):
    __tablename__ = 'chatrooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    host_id = db.Column(db.String(50), nullable=False, default='default')
    # 添加密钥字段
    public_key = db.Column(db.Text, nullable=False)  # 存储公钥
    private_key = db.Column(db.Text, nullable=False)  # 存储私钥

    # 关系
    owner = db.relationship('User', backref='owned_rooms', foreign_keys=[owner_id])
    members = db.relationship('User', secondary=chatroom_members, 
                            backref=db.backref('chatrooms', lazy='dynamic'),
                            cascade='all, delete')
    messages = db.relationship('ChatMessage', backref='room', lazy=True, 
                             cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'owner_id': self.owner_id,
            'host_id': self.host_id,
            'members': [user.username for user in self.members],
            'public_key': self.public_key
        }

# 修改 ChatMessage 模型，添加聊天室关联
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('chatrooms.id', ondelete='CASCADE'), nullable=False)
    host_id = db.Column(db.String(50), default='default')

    # 添加索引以提高查询性能
    __table_args__ = (
        db.Index('idx_room_timestamp', room_id, timestamp),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': self.user_id,
            'room_id': self.room_id,
            'host_id': self.host_id,
            'username': self.author.username if self.author else 'Unknown'
        }

class MessageBroker:
    def __init__(self, redis_client):
        self.redis = redis_client
        if self.redis:
            self.pubsub = self.redis.pubsub()
        
    def publish_post(self, post):
        if not self.redis:
            return
        message = {
            'type': 'post',
            'data': post.to_dict()
        }
        self.redis.publish('forum_channel', json.dumps(message))
        
    def publish_chat(self, chat_message):
        if not self.redis:
            return
        message = {
            'type': 'chat',
            'data': {
                'id': chat_message.id,
                'content': chat_message.content,  # 已加密的消息内容
                'user_id': chat_message.user_id,
                'room_id': chat_message.room_id,
                'host_id': chat_message.host_id,
                'username': chat_message.author.username,
                'timestamp': chat_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        try:
            self.redis.publish('forum_channel', json.dumps(message))
            print(f"加密消息已发布到Redis")
        except Exception as e:
            print(f"发布消息到Redis时出错: {e}")
        
    def publish_user(self, user):
        if not self.redis:
            return
        message = {
            'type': 'user',
            'data': user.to_dict()
        }
        self.redis.publish('forum_channel', json.dumps(message))

message_broker = MessageBroker(redis_client)

