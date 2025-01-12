from flask import Flask, render_template, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from database import db, migrate, User, Post, ChatMessage, message_broker, redis_client, ChatRoom
from datetime import datetime
from crypto_utils import ChatRoomCrypto
import os
import socket
import uuid
import json
import threading

# 初始化加密工具
crypto = ChatRoomCrypto()

# 生成唯一的主机ID和端口相关的用户名
HOST_ID = str(uuid.uuid4())
PORT = int(os.environ.get('PORT', 5001))
USERNAME = f'user_port_{PORT}'  # 基于端口号创建唯一用户名
EMAIL = f'user_{PORT}@example.com'  # 基于端口号创建唯一邮箱

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化扩展
db.init_app(app)
migrate.init_app(app, db)
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

@socketio.on('connect')
def handle_connect():
    print("客户端连接成功")
    
@socketio.on('disconnect')
def handle_disconnect():
    print("客户端断开连接")

# Redis 订阅处理
def handle_redis_messages():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('forum_channel')
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                if data['type'] == 'chat':
                    chat_data = data['data']
                    if chat_data['host_id'] != HOST_ID:  # 只处理其他主机的消息
                        with app.app_context():
                            # 获取聊天室和解密消息
                            room = ChatRoom.query.get(chat_data['room_id'])
                            if not room:
                                print(f"未找到聊天室: {chat_data['room_id']}")
                                continue
                                
                            # 解密消息内容
                            decrypted_content = crypto.decrypt_message(chat_data['content'], room.private_key)
                            if not decrypted_content:
                                print("消息解密失败")
                                continue
                            
                            # 检查消息是否已存在
                            existing_message = ChatMessage.query.filter_by(
                                content=chat_data['content'],
                                user_id=chat_data['user_id'],
                                room_id=chat_data['room_id'],
                                host_id=chat_data['host_id']
                            ).first()
                            
                            if not existing_message:
                                # 保存消息到数据库
                                user = User.query.get(chat_data['user_id'])
                                if user:
                                    chat_message = ChatMessage(
                                        content=chat_data['content'],  # 保存加密的消息
                                        user_id=user.id,
                                        room_id=chat_data['room_id'],
                                        host_id=chat_data['host_id']
                                    )
                                    db.session.add(chat_message)
                                    db.session.commit()
                                    print(f"已保存来自其他实例的消息")
                            
                            # 广播解密后的消息到房间
                            message_data = {
                                'room_id': str(chat_data['room_id']),
                                'user': chat_data['username'],
                                'message': decrypted_content,  # 发送解密后的消息
                                'timestamp': chat_data['timestamp']
                            }
                            print(f"Redis广播消息到房间 {chat_data['room_id']}: {message_data}")
                            socketio.emit('message', message_data, room=str(chat_data['room_id']))
                            
            except Exception as e:
                print(f"处理Redis消息时发生错误: {e}")
                if 'db' in locals() and hasattr(db, 'session'):
                    db.session.rollback()

# 启动Redis监听线程
redis_thread = threading.Thread(target=handle_redis_messages)
redis_thread.daemon = True
redis_thread.start()

def get_current_user():
    """获取当前端口对应的用户"""
    try:
        # 确保在应用上下文中执行
        if not app.app_context():
            return None
            
        # 查找或创建用户
        user = User.query.filter_by(username=USERNAME).first()
        if not user:
            # 创建新用户
            user = User(
                username=USERNAME,
                email=EMAIL,
                password_hash='test123',
                host_id=HOST_ID
            )
            try:
                db.session.add(user)
                db.session.commit()
                print(f"新用户创建成功: {USERNAME}")
            except Exception as e:
                db.session.rollback()
                print(f"创建用户失败: {e}")
                return None
        return user
    except Exception as e:
        print(f"获取用户失败: {e}")
        if 'db' in locals() and hasattr(db, 'session'):
            db.session.rollback()
        return None

def init_database():
    """初始化数据库"""
    try:
        with app.app_context():
            # 删除所有表（如果存在）
            db.drop_all()
            print("已删除旧表")
            
            # 创建所有表
            db.create_all()
            print("已创建新表")
            
            # 确保当前用户存在
            user = get_current_user()
            if user:
                try:
                    # 发布用户信息到其他实例
                    message_broker.publish_user(user)
                    print(f"数据库初始化成功！当前用户: {USERNAME}")
                except Exception as e:
                    print(f"发布用户信息失败: {e}")
            else:
                print("警告: 未能创建用户")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        if 'db' in locals() and hasattr(db, 'session'):
            db.session.rollback()
        raise e

# 修改路由处理函数，添加错误处理
@app.route('/')
def home():
    try:
        posts = Post.query.order_by(Post.date_posted.desc()).all()
        current_user = get_current_user()
        if not current_user:
            flash('获取用户信息失败', 'error')
            return render_template('home.html', posts=posts, current_user=None)
        return render_template('home.html', posts=posts, current_user=current_user)
    except Exception as e:
        flash(f'发生错误: {str(e)}', 'error')
        return render_template('home.html', posts=[], current_user=None)

@app.route('/post', methods=['POST'])
def post():
    try:
        user = get_current_user()
        if not user:
            flash('请先登录', 'warning')
            return redirect(url_for('home'))
        
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('标题和内容不能为空', 'danger')
            return redirect(url_for('home'))
        
        # 检查是否已存在相同的帖子
        existing_post = Post.query.filter_by(
            title=title,
            content=content,
            user_id=user.id,
            host_id=HOST_ID
        ).first()
        
        if existing_post:
            flash('该帖子已存在', 'warning')
            return redirect(url_for('home'))
        
        # 创建新帖子
        post = Post(
            title=title,
            content=content,
            user_id=user.id,
            host_id=HOST_ID
        )
        db.session.add(post)
        db.session.commit()
        
        # 发布到其他主机
        message_broker.publish_post(post)
        flash('发布成功！', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash(f'发布失败: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route('/chat')
@app.route('/chat/<int:room_id>')
def chat(room_id=None):
    current_user = get_current_user()
    if not current_user:
        flash('获取用户信息失败', 'error')
        return redirect(url_for('home'))
    
    # 获取用户的所有聊天室（已加入的）
    user_rooms = current_user.chatrooms.all()
    
    # 获取所有聊天室（包括未加入的）
    all_rooms = ChatRoom.query.all()
    
    # 获取活动的聊天室和历史消息
    active_room = None
    chat_history = []
    available_users = []
    
    if room_id:
        active_room = ChatRoom.query.get(room_id)
        if not active_room:
            flash('聊天室不存在', 'error')
            return redirect(url_for('chat'))
            
        # 检查用户是否是该聊天室的成员
        is_member = current_user in active_room.members
        
        if not is_member:
            flash('你不是该聊天室的成员，无法查看内容', 'warning')
            return redirect(url_for('chat'))
        
        # 获取聊天历史记录，按时间正序排列
        encrypted_messages = ChatMessage.query.filter_by(room_id=room_id)\
            .order_by(ChatMessage.timestamp.asc())\
            .all()
        
        print(f"获取到 {len(encrypted_messages)} 条历史消息")
        
        # 解密并转换消息格式
        chat_history = []
        for msg in encrypted_messages:
            try:
                decrypted_content = crypto.decrypt_message(msg.content, active_room.private_key)
                if decrypted_content:
                    chat_history.append({
                        'room_id': str(msg.room_id),
                        'user': msg.author.username if msg.author else 'Unknown',
                        'message': decrypted_content,
                        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    })
            except Exception as e:
                print(f"解密消息失败: {e}")
        
        print(f"处理后的历史消息: {len(chat_history)} 条")
        
        # 获取可邀请的用户列表（仅聊天室创建者可见）
        if current_user.id == active_room.owner_id:
            available_users = User.query.filter(
                ~User.id.in_([m.id for m in active_room.members])
            ).all()
    
    # 确保在模板中传递所有必要的变量
    return render_template('chat.html', 
                         current_user=current_user,
                         active_room=active_room,
                         user_rooms=user_rooms,
                         all_rooms=all_rooms,
                         available_users=available_users,
                         chat_history=chat_history)

@app.route('/chat/create', methods=['POST'])
def create_room():
    current_user = get_current_user()
    if not current_user:
        flash('请先登录', 'error')
        return redirect(url_for('chat'))
    
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('聊天室名称不能为空', 'error')
        return redirect(url_for('chat'))
    
    try:
        # 生成聊天室密钥对
        keys = crypto.generate_room_keypair()
        
        room = ChatRoom(
            name=name,
            description=description,
            owner_id=current_user.id,
            host_id=HOST_ID,
            public_key=keys['public_key'],
            private_key=keys['private_key']
        )
        room.members.append(current_user)  # 创建者自动加入聊天室
        
        db.session.add(room)
        db.session.commit()
        
        flash('聊天室创建成功！', 'success')
        return redirect(url_for('chat', room_id=room.id))
    except Exception as e:
        db.session.rollback()
        flash(f'创建聊天室失败: {str(e)}', 'error')
        return redirect(url_for('chat'))

@app.route('/chat/<int:room_id>/invite', methods=['POST'])
def invite_user(room_id):
    current_user = get_current_user()
    room = ChatRoom.query.get_or_404(room_id)
    
    if current_user.id != room.owner_id:
        flash('只有聊天室创建者可以邀请用户', 'error')
        return redirect(url_for('chat', room_id=room_id))
    
    user_ids = request.form.getlist('user_id')
    for user_id in user_ids:
        user = User.query.get(user_id)
        if user and user not in room.members:
            room.members.append(user)
    
    db.session.commit()
    flash('邀请发送成功！', 'success')
    return redirect(url_for('chat', room_id=room_id))

@socketio.on('join')
def on_join(data):
    """处理加入房间事件"""
    try:
        room_id = str(data.get('room_id'))
        print(f"正在处理加入房间请求: {room_id}")
        
        if room_id and room_id != 'null':
            join_room(room_id)
            print(f"用户成功加入房间: {room_id}")
            
            # 发送加入通知
            user = get_current_user()
            if user:
                system_message = {
                    'room_id': room_id,
                    'message': f'{user.username} 加入了聊天室',
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                }
                emit('system_message', system_message, room=room_id)
                print(f"已发送系统消息: {system_message}")
    except Exception as e:
        print(f"加入房间失败: {e}")

@socketio.on('leave')
def on_leave(data):
    """处理离开房间事件"""
    try:
        room_id = str(data.get('room_id'))
        if room_id and room_id != 'null':
            leave_room(room_id)
            print(f"用户离开房间: {room_id}")
    except Exception as e:
        print(f"离开房间失败: {e}")

@socketio.on('message')
def handle_message(data):
    """处理聊天消息"""
    try:
        print(f"收到 WebSocket 消息: {data}")
        user = get_current_user()
        if not user:
            print("未找到用户")
            emit('error', {'message': '未找到用户'})
            return
        
        room_id = str(data.get('room_id'))
        content = data.get('content', '').strip()
        
        print(f"处理消息 - 房间: {room_id}, 内容: {content}, 用户: {user.username}")
        
        if not room_id:
            print("无效的房间ID")
            emit('error', {'message': '无效的房间ID'})
            return
            
        if not content:
            print("消息内容为空")
            emit('error', {'message': '消息内容不能为空'})
            return
        
        try:
            room = ChatRoom.query.get(int(room_id))
            if not room:
                print(f"未找到房间: {room_id}")
                emit('error', {'message': '未找到聊天室'})
                return
                
            if user not in room.members:
                print(f"用户 {user.username} 不是房间 {room_id} 的成员")
                emit('error', {'message': '你不是该聊天室的成员'})
                return
            
            # 准备消息数据
            message_data = {
                'room_id': room_id,
                'user': user.username,
                'message': content,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            try:
                # 加密消息内容
                print(f"开始加密消息，公钥长度: {len(room.public_key) if room.public_key else 0}")
                encrypted_content = crypto.encrypt_message(content, room.public_key)
                if not encrypted_content:
                    print("消息加密失败，可能是公钥无效")
                    emit('error', {'message': '消息加密失败，请联系管理员'})
                    return
                print("消息加密成功")
                
                # 创建并保存消息
                chat_message = ChatMessage(
                    content=encrypted_content,
                    user_id=user.id,
                    room_id=int(room_id),
                    host_id=HOST_ID
                )
                db.session.add(chat_message)
                db.session.commit()
                print("消息已保存到数据库")
                
                # 发送到当前房间的所有用户
                socketio.emit('message', message_data, room=room_id)
                print(f"消息已广播到房间 {room_id}")
                
                # 发布到其他实例
                message_broker.publish_chat(chat_message)
                print("消息已发布到其他实例")
                
            except Exception as e:
                print(f"保存消息时出错: {str(e)}")
                db.session.rollback()
                emit('error', {'message': '消息处理失败'})
                return
                
        except ValueError as e:
            print(f"房间ID转换错误: {str(e)}")
            emit('error', {'message': '无效的房间ID'})
            return
            
    except Exception as e:
        print(f"处理消息时发生错误: {str(e)}")
        if 'db' in locals() and hasattr(db, 'session'):
            db.session.rollback()
        emit('error', {'message': '系统错误'})

@app.route('/profile')
def profile():
    try:
        user = get_current_user()
        if not user:
            flash('获取用户信息失败', 'error')
            return redirect(url_for('home'))
        
        user_posts = Post.query.filter_by(user_id=user.id).order_by(Post.date_posted.desc()).all()
        return render_template('profile.html', user=user, user_posts=user_posts)
    except Exception as e:
        flash(f'发生错误: {str(e)}', 'error')
        return redirect(url_for('home'))

if __name__ == '__main__':
    try:
        # 确保 instance 目录存在
        if not os.path.exists('instance'):
            os.makedirs('instance')
            print("创建 instance 目录")
        
        # 删除旧的数据库文件
        db_path = 'instance/site.db'
        if os.path.exists(db_path):
            os.remove(db_path)
            print("已删除旧的数据库文件")
        
        # 初始化数据库
        with app.app_context():
            init_database()
            
            # 验证数据库连接
            try:
                db.session.execute('SELECT 1')
                print("数据库连接测试成功")
            except Exception as e:
                print(f"数据库连接测试失败: {e}")
                raise e
        
        print(f"服务器将在 http://localhost:{PORT} 启动")
        print(f"当前用户: {USERNAME}")
        
        # 启动服务器
        socketio.run(app, 
                    host='0.0.0.0',
                    port=PORT,
                    debug=True)
    except Exception as e:
        print(f"启动服务器时发生错误: {e}")


