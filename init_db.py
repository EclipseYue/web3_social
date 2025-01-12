from app import app, db
from database import User, Post, ChatMessage

def init_db():
    with app.app_context():
        # 删除所有表
        db.drop_all()
        print("已删除所有表")
        
        # 创建所有表
        db.create_all()
        print("已创建新表")

if __name__ == '__main__':
    init_db() 